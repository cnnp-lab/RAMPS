# RAMP
 Resection Automation Mask in Pre-operative space


## How to setup the code
1. Clone this repository. 
2. Create a virtual python 3.8.20 enviroment (e.g via conda https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html) and install the requirements.txt. Example of code to do this is via the following.

```
conda create -n RAMPenv python=3.8.20
conda activate RAMPenv
pip install -r requirements.txt
```

4. Clone the https://github.com/BBillot/SynthSeg repository and place it inside "Place_SynthSeg_here". No additional python modules has to be installed. Make sure to follow SynthSeg step 3 and place the additional models in the SynthSeg models folder. (Link to these additional models can be found here [Here](https://liveuclac-my.sharepoint.com/personal/rmappmb_ucl_ac_uk/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Frmappmb%5Fucl%5Fac%5Fuk%2FDocuments%2Fsynthseg%20models&ga=1)
7. Ensure that freesurfer is installed (https://surfer.nmr.mgh.harvard.edu/) here is the link to the freesurfer set up [MAC tutorial](https://surfer.nmr.mgh.harvard.edu/fswiki//FS7_mac) and [Linux tutorial ](https://surfer.nmr.mgh.harvard.edu/fswiki//FS7_linux). Also check that the system enviroment 'FREESURFER_HOME' is set up and works correctly. To make this easier Its reccomened that you add somthing like the following to your shell startup (see freesurfer documentation for more information)
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
This code can be broken down into 3 steps - 
- PREPARING which is the steps taken to get the pre and post scans ready for registration  
- REGISTRATION which is code needed to align the post-op image into the pre-operative space
- CREATION which is the code that creates the mask once the images are alligned in the same space

### A - PREPARING
- First convert the pre and post op images into orig resolution via ants resample_image_to_target
- Use N4bias to correct the bias feild
- mri_synthstrip is applied to strip the image up to the pial surface
- SynthSeg is used to segmentate the brain into a parcellation scheme - to become a mask of the brain and the lobes
- Use the Synthseg mask to the pial surface
- The use SynthSeg parcellation to group regions into the lobe.
- Dilate each lobe to get the attached White matter for each lobe
- Create a mask of the resected and none resected lobes
- Extract the ventricles
- Remove the top 1% of voxel intensity and replace them with the median no CSF voxel value

### B - REGISTRATION   
- Transform the cleaned post-operative image into the pre-operative space via the use of antsRegistrationSyN[br]

### C - CREATION 
- Rescale the pre and post operative between 0 and 1
- Create a mask of each pre and post op images
- Get the difference between the two mask
- move the post op vents into pre-op space
- use atropos to find the resection in the post-op tissue (thats in pre-op space) by looking for voxels that are similar to the vents
- Subtract the post-op image from the pre-op image
- Use atropos to exapnd the post-op resection mask through the Subtraction space
- filter to resected lobe , get largest object and dilate by 1 voxel, add the difference the pre and post mask
- This get resection mask 1
- errode the resection mask by 1
- dilate the resection mask and check what has been added to the mask. If the expansion is only a few voxels then we highlight that area as a region to advoid further expansion
- Repate this until the diffrence between dilation is only 100 voxels
- Expand the mask into voxels that are between the voxels in the mask and CSF voxel that is only 3 voxels away
- add the difference the pre and post mask
- This creates mask 2

Here is an image outlining how it works (rough figure being worked on)
![screenshot](https://github.com/ItCallum/RAMP/tree/main/FIG/RAMP_methods_FIG.png?raw=true)








