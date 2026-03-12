# RAMPS - Resections And Masks in Preoperative Space
An automated pipeline that generates 3D masks of pre-operative tissue resected, leveraging existing software including FreeSurfer, SynthStrip, Sythnseg and ANTS to aid in this task.

For a breif overview: 
- RAMPS works by finding the cluster of difference between the pre and post operative t1w images.
- Though the masks produce by RAMPS produce are inline with 'gold standard interpretation', RAMPS mask is slightly larger
- While the pipeline can run without information of lobe and hemisphere, we recommend providing this information where possible, as it consistently yields the most accurate results.
- We always recommened that mask outputs are manually inpsected to ensure they meet standards
  
## How to cite 
If you use RAMPS please reference us using:

Simpson C, Hall G, Duncan JS, Wang Y, Taylor PN. Automated generation of epilepsy surgery resection masks: The RAMPS pipeline. Imaging Neurosci (Camb). 2025 Sep 10;3:IMAG.a.147. doi: 10.1162/IMAG.a.147. PMID: 40948604; PMCID: PMC12423638.

## How to setup the code
1. Clone this repository. 
2. Create a virtual python 3.8.20 enviroment (e.g via conda https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html) and install the requirements.txt. Example of code to do this is via the following.

```
conda create -n RAMPenv python=3.8.20
conda activate RAMPenv
pip install -r requirements.txt
```

3. Clone the https://github.com/BBillot/SynthSeg repository and place it inside "Place_SynthSeg_here". No additional python modules has to be installed. Make sure to follow SynthSeg step 3 and place the additional models in the SynthSeg models folder. (Extra information about this can be found on the SynthSeg page [Found here](https://github.com/BBillot/SynthSeg), due to an ongoing issue with the orignal storage of the models changing, please find the required models [here](https://github.com/BBillot/SynthSeg/issues/114) 
4. Ensure that freesurfer is installed (https://surfer.nmr.mgh.harvard.edu/) here is the link to the freesurfer set up [MAC tutorial](https://surfer.nmr.mgh.harvard.edu/fswiki//FS7_mac) and [Linux tutorial ](https://surfer.nmr.mgh.harvard.edu/fswiki//FS7_linux). Also check that the system enviroment 'FREESURFER_HOME' is set up and works correctly. To make this easier Its reccomened that you add somthing like the following to your shell startup (see freesurfer documentation for more information)
```
export FREESURFER_HOME=$HOME/freesurfer
$ source $FREESURFER_HOME/SetUpFreeSurfer.sh
```

## Run the command
Once all the python packages are installed and Freesurfer and SynthSeg is installed then you can test RAMP with the following 

```
python /Path_to/RAMP.py </Path_to/Pre-OP-Scan.nii.gz> </Path_to/Post-OP-Scan.nii.gz> </Path_to_Output_Folder_file_path/> <Output_Prefix> <Hemisphere> <Lobe>
```

where:
- <Pre-OP-Scan.nii.gz> is the absolute path to the pre operation nii.gz file (which is the space that the mask will be drawn in)
- <Post-OP-Scan.nii.gz> is the absolute path to the post operation nii.gz file 
- <Output_Folder_file_path> This is the folder path to the place where you want to store the outputs of this script
- <Output_Prefix> an ID to use in the naming of the scripts
- <Hemisphere> L or R. Is the hemisphere in which the resection took place either L or R
- <Lobe> any combination of T F O P . this is to select the lobe of resection. Example T will just be the temporal lobe while TF will look at the frontal and temporal lobe. Note for ease of use Temporal inludes the Temporal, subcortical and Insula region.


## Example of how it works 
Lets say we have a patient X which we see a resection takes place in the Right Frontal lobe, the command to run this will be.

```
python /Path_to/RAMP.py patient_X-PRE-OP-Scan.nii.gz patient_X-POST-OP-Scan.nii.gz patient_X-Output_Folder_file_path patient_X R F
```

## How this code works
Using a T1w pre- and post-operative image, as well as hemisphere and lobe of resection, RAMPS generates a mask of resected pre-operative tissue in 3 steps - 
- DATA PREPARATION : series of steps are undertaken to remove noise from the image, extract the brain tissue and create a lobe atlas map of the brain 
- REGISTRATION : uses ANTs registration to align the post-operative brain to the pre-operative
- MASK CREATION : involves delineating the resection cavity in the post-operative space resection and then expanding to the pre-operative tissue boundary

The overview of the RAMPS pipeline

![RAMPSworks](https://github.com/cnnp-lab/RAMPS/blob/main/FIG/HowRAMPSworks.png)


### A - PREPARING
- Step 1 - Resolution normalisation : First apply the ANTS resample_image_to_target function to resample images into 1 x 1 x 1 mm resolution with 265 * 256 * 256 fov. This keeps the images in their original space while standardizing FOV and voxel size.
- Step 2 - Bias intensity correction : Images are then ran through ants.n4_bias_field_correction to correct any low frequency intensity non-uniformity present in MRI image data known as a bias or gain field. This corrects the slow and smooth intensity variation across the image, thereby reducing field bias. At the end of part A, to further ensure bias removal, the top 1\% voxels values were replaced by the median voxel value. 
- Step 3 - Brain extraction : Removal of non-brain elements (i.e skull, eyes etc) reduces potential complications in the segmentation and registration step, especially around the resection cavity. The skull-stripping tool SynthStrip is used remove non-brain elements from the T1w images. SynthStrip has been shown to be a robust model and agnostic to acquisition specifics. 
- Step 4 - Regional segmentation : Through the use of SynthSeg, the images are segmentated into a series of atlas regions. SynthSeg is robust across various brain scans of differing contrast and resolution. Atlas regions are then joined via lobe to create a grey-matter lobe atlas map of the following regional categories: Frontal, Parietal, Temporal, Occipital, Insula, Sub-Cortical areas and areas in which the resection cannot occur (such as ventricles, brainstem and cerebellum). Additionally, the SynthStrip brain image is multiplied by a binarised mask made from the SynthSeg segmented atlas, The rationale is to eliminate any remaining non-brain elements or residual surface left in the image, particularly around the resection cavity.
- Step 5 - Lobe of resected area: The grey-matter lobe atlas map is dilated throughout the white matter to create a full lobe map. The dilated atlas is subsequently divided into two binary masks based on users specification: the hemisphere-specific lobe where the resection occurred, and the other lobes where the resection did not occur.

### B - REGISTRATION   
- Step 6 - Registration : At this stage, the T1w images have been cleaned but still exist in different coordinate spaces. Before creating the resection mask, align the tissue in the post-operative image to the pre-operative image. Due to the sagging and swelling that may be seen in post-operative image, this alignment is critical, as poor alignment could erroneously cause further misalignment of tissue. The ANTS antsRegistrationSyN rigid + deformable b-spline syn approach, was found to be accurate in the presence of sagging and swelling. In addition the calculated transformations are used to move information created from the post-operative image into the pre-operative space.

### C - Cavity classification 
Following registration, the post-operative image exists in the pre-operative space and the following steps produce a resection mask in pre-operative space. 

- Step 7 - Rescale : To contrast the pre- and post-operative images against one another, first rescale the images between 0 and 1, to ensure that the cerebrospinal fluid (CSF), grey matter and white matter exhibit similar voxel values across images.
- Step 8 - Post-operative image atropos: Next, we delineate the resection cavity within the post-operative image. This is achieved through ANTs Atropos, an open source finite mixture modeling algorithm for tissue segmentation. Here we use Atropos with Prior Label Image initialization, a clustering technique that groups voxels based on a prior segmentation of each class. The prior images used here consist of 1) ventricles for classification of cerebrospinal fluid (CSF) and 2) cerebral tissue in the non-resected lobes. This classifies the voxels in the resected lobe into 1) the resection cavity and 2) non-resected tissue. 
- Step 9 - The previous step classifies the image based on similarities to the prior voxel intensities, however in-between voxels correspond to damaged tissue may be included in the resection cavity. To separate the damaged tissue from CSF, a no prior image two group K-mean Atropos classification was applied within the step-8 resection cavity. As no voxel priors are utilised, the cluster with the lowest median voxel intensity is classed as CSF.
- Step 10 - Image subtraction:  Next subtract the post-operative rescaled image from the pre-operative rescaled image to create a difference image. This approach is based on the rationale that after step 7, subtraction of the same voxel class (grey matter, white matter and CSF) will roughly equal zero, whereas overlap of differing classes will not equal zero. This highlights the overlap between the resection cavity observed in the post-operative image (CSF) and tissue in the pre-operative image, and indicates where sagging has occurred within the image. The resulting subtraction image is then multiplied by the mask of pre-operative image, highlighting the areas of tissue difference in the pre-operative image.
- Step 11 - Atropos through subtraction image : Similar to step 8, Atropos is used with a prior image to expand the post-op resection cavity through the subtraction image. This highlights the voxels in the subtracted images where the images differ. Additionally, the results of this Atropos is filtered to the lobe in which resection take place and the largest object is selected to be the mask of the resection cavity.
- Step 12 - Cavity removal : A common issue with the subtraction image arises from poor registration, leading to differences caused by tissue misalignment and not resection. These sections of poor alignment are often attached to the main resection mask via narrow contact points of a few voxels. These areas of noise can be removed by first eroding the mask and performing a series of small dilations through the original mask. After each dilation we examine the voxels expanded into. If expansion reveals a small cluster of voxels, it indicates that there is an area of poor alignment. Further dilation into this region is prevented, re-creating the step 11 mask, but removing these areas of misalignment.
- Step 13 - Boundary dilation : To ensure that the mask extends to the appropriate tissue boundary, a directional dilation is performed. If a given voxel on the boundary of the mask is within 3 voxels of CSF, all voxels between the two points are added to the mask. This stops the dilation into tissue that was not resected.
- Step 14 - Additional cleaning : ANTs morphology is applied to fill any small cavities within the resection mask. Then the mask is multiplied by a binarised mask of the pre-operative lobe of resection to remove any voxels that might exist outside this region. Finally, the resection mask is resampled back into the pre-operative resolution.

## Results from paper

We show RAMPS preformance against a cohort of 87 manual masks, the results are seen here. 

![RAMPSresults](https://github.com/cnnp-lab/RAMPS/blob/main/FIG/RAMPS_results.png)

Additionally we show RAMPS perfromance under a range of different resection cavity tasks. 

![RAMPSresults](https://github.com/cnnp-lab/RAMPS/blob/main/FIG/RAMPS_results_v2.png)




