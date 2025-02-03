# ========================================
# RAMPS
# Resection Automated Mask in Pre-operative Space
# By Callum Simpson
# ========================================

# The aim of this code is to segment the preoperative image tissue shown to be resected in the post op image.
# General overview
# This code can be broken down into 3 steps -
# - PREPARING which is the steps taken to get the pre and post scans ready for registration
# - REGISTRATION which is code needed to align the post-op image into the pre-operative space
# - CREATION which is the code that creates the mask once the images are alligned in the same space


# ========================================
### Imports ---

import pandas as pd
import ants
import time
import os.path
import nibabel as nib
import numpy as np
import numpy.ma as ma
from scipy import ndimage as nd
import sys

# Get the location of this script is, to keep all this code in the same place
Location_of_script = os.path.dirname(os.path.abspath(__file__))

#Get freesurfer_home
FREESURFER_HOME=os.environ['FREESURFER_HOME']

#Get the python scripts for synthstrip and synthseg
mri_synthstrip = FREESURFER_HOME+"/python/scripts/mri_synthstrip"
mri_synthseg = str(Location_of_script)+"/Place_SynthSeg_here/SynthSeg/scripts/commands/SynthSeg_predict.py"

# ========================================
### Inputs ---

## Pre_op_data - a nii.gz image of the pre-operative image
#PreOP_Data_image=sys.argv[1]

## Post_op_data - a nii.gz image of the post-operative image
#PostOP_Data_image=sys.argv[2]

## The location where this data will be generated
#Output_Folder=sys.argv[3]

##What are we going to name the files (usally patient ID)
#Output_Prefix=sys.argv[4]

# Hemisphere L or R
#Hemisphere=sys.argv[5]

# Lobe
# Must be the Frist letter of the lobe in brackets
# Lobe_intro=T
# Lobe_intro=TFOP
# T - Temporal (and subcortical)
# F - Frontal
# O - Occipital
# P - Parietal
#Lobe_intro=sys.argv[6]

# Location of fake ORIG file
#blank_orig=str(Location_of_script)+"/fakesurfer_orig.nii.gz"
#blank_orig = ants.image_read(blank_orig)

## Break the Lobestring into an array

#Lobe=list(Lobe_intro)
#print("-- done the lobes ---")
#print(Lobe)


# ========================================
### Inputs checks ---


print("")
print("")
print("================================================== ")
print("                RAMPS")
print(" Resection Automated Mask in Pre-operative Space")
print("            By Callum Simpson")
print("================================================== ")
print("")
print("> RAMPS input check ")

if len(sys.argv) != 7:
    print("Error - not all inputs where detected")
    print("Usage: RAMPS.py < PreOP_image.nii.gz > < PostOP_image.nii.gz > < Output folder path > < Output prefix/ID > < Hemisphere [L/R] > < Lobes of resection [T/F/O/P] > ")
    sys.exit(1)


### Check the PRE-op ---
## Pre_op_data - a nii.gz image of the pre-operative image
PreOP_Data_image = sys.argv[1]

if not os.path.isfile(PreOP_Data_image):
    print("Error - This file is not detected : " + PreOP_Data_image)
    sys.exit(1)


if not PreOP_Data_image.endswith("nii.gz"):
    print("Error - Epected pre-op image to end with nii.gz")
    sys.exit(1)

### Check the POST-op ---
## Post_op_data - a nii.gz image of the pre-operative image
PostOP_Data_image = sys.argv[2]

if not os.path.isfile(PostOP_Data_image):
    print("Error - This file is not detected : " + PostOP_Data_image)
    sys.exit(1)


if not PostOP_Data_image.endswith("nii.gz"):
    print("Error - Epected post-op image to end with nii.gz")
    sys.exit(1)

### Check the Output ---
## The location where this data will be stored
Output_Folder=sys.argv[3]

if not os.path.isdir(Output_Folder):
    print("Error - The output folder cannot be detected")
    sys.exit(1)

### Check the Output_Prefix ---
# As this is user defined we will allow them to choose an appropiate ID
Output_Prefix=sys.argv[4]


### Check the Inputed Hemisphere ---
# this has to be either L or R
Hemisphere=sys.argv[5]
Hemisphere=str(Hemisphere)
Hemisphere=Hemisphere.upper()

if Hemisphere not in ["L","R"]:
    print("Error - Hemisphere not properly defined, must be L or R")
    sys.exit(1)

### Check the lobe ---
# Lobe
# Must be the Frist letter of the lobe in brackets
# Lobe_intro=T
# Lobe_intro=TFOP
# T - Temporal (and subcortical)
# F - Frontal
# O - Occipital
# P - Parietal
Lobe_intro=sys.argv[6]
Lobe_intro =str(Lobe_intro)
Lobe_intro = Lobe_intro.upper()
Lobe=list(Lobe_intro)

Valid_lobes=['T','F','O','P']

Lobe = [element for element in Lobe if element in Valid_lobes]

# Check if the additional files are set up
# Location of fake ORIG file
blank_orig=str(Location_of_script)+"/fakesurfer_orig.nii.gz"

if os.path.isfile(blank_orig):
    print("> Blank orig image found")
    blank_orig = ants.image_read(blank_orig)
else:
    print("Error: Blank orig image not found at :" + str(Location_of_script)+"/fakesurfer_orig.nii.gz")
    sys.exit(1)


if os.path.isfile(FREESURFER_HOME+"/python/scripts/mri_synthstrip"):
    print("> mri_synthstrip found")
else:
    print("Error: Cannont find mri_synthstrip at :" + FREESURFER_HOME+"/python/scripts/mri_synthstrip")
    sys.exit(1)

if os.path.isfile(str(Location_of_script)+"/Place_SynthSeg_here/SynthSeg/scripts/commands/SynthSeg_predict.py"):
    print("> SynthSeg found")
else:
    print("Error: Cannont find SynthSeg at:" + str(Location_of_script)+"/Place_SynthSeg_here/SynthSeg/scripts/commands/SynthSeg_predict.py")
    sys.exit(1)


print(">  All the inputs look good")
print("")
print("-------------------")
print("       RAMPS       ")
print("-------------------")

print(">  The Hemisphere of resection --> " + Hemisphere)

print(">  The lobes of resection  --> " + str(Lobe))



# ========================================
# 0.3 Time keeping
# Create a spreadsheet that tracks how long each section is taking
# ========================================

Time_keeping = pd.DataFrame(columns=['Section','Time_(SEC)'])

# ========================================
# 1 - Get the image into orig resolution
# We want an orig file but don't want to run somthing like recon-all that will take alot of time
# Instead we apply ants resample_image_to_target. All this does is change the resolution of the image to the same of orig
# ========================================

start = time.time()

# First we
# --- Pre-op

# extract the file name from the inputted folder path
ID_PreOP = os.path.basename(PreOP_Data_image)
ID_PreOP = ID_PreOP.split(".")[0]

# Create the folders the store the mri file
PreOP_Data_Folder=os.path.join(Output_Folder, ID_PreOP)
PreOP_Data_Folder_mri=os.path.join(PreOP_Data_Folder,'mri')

if not os.path.exists(PreOP_Data_Folder):
    os.makedirs(PreOP_Data_Folder)
    os.makedirs(PreOP_Data_Folder_mri)
    
PreOP_Data_image = ants.image_read(PreOP_Data_image)

# resample the image into that of orig space
pre_op_fake=ants.resample_image_to_target(PreOP_Data_image,blank_orig)
pre_op_fake.image_write(PreOP_Data_Folder_mri+"/orig.nii.gz",ri=True)

ID_PostOP = os.path.basename(PostOP_Data_image)
ID_PostOP = ID_PostOP.split(".")[0]

# --- Post-op

# Create the folders the store the mri file
PostOP_Data_Folder=os.path.join(Output_Folder, ID_PostOP)
PostOP_Data_Folder_mri=os.path.join(PostOP_Data_Folder,'mri')

if not os.path.exists(PostOP_Data_Folder):
    os.makedirs(PostOP_Data_Folder)
    os.makedirs(PostOP_Data_Folder_mri)
    
PostOP_Data_image = ants.image_read(PostOP_Data_image)

post_op_fake=ants.resample_image_to_target(PostOP_Data_image,blank_orig)
post_op_fake.image_write(PostOP_Data_Folder_mri+"/orig.nii.gz",ri=True)


end = time.time()

recorded_time=end-start
print(recorded_time)

Time_keeping = pd.concat([Time_keeping, pd.DataFrame(['Fake_Orig',recorded_time])], ignore_index=True)

# ========================================
# 2 - Refined skull stripping
# When using tools like ANTs and Atropos, it's crucial that images undergo skull stripping to remove any remaining skull. Failure to do so can lead to issues during processing. Additionally, FastSurfer results sometimes exhibit harshness around the resection area, potentially resulting in regions being falsely identified as "resected" due to artifacts from the skull stripping process. Through testing, it's been observed that employing mri_synthstrip with the --no-csf option can produce cleaner results with fewer skull fragments and smoother cuts around the resection area.
# What the next set of code allows is us to perform a brain extraction on the images that keeps the shape of the brain even if apart of it has been resected (keeps the resection cavity within the image but gets rid of any bits of skull or tissue that likes with the resection cavity).
# First N4bias the image to remove noise
# We achieve this by using mri_synthstrip to skull strip the image but trying to keep the pial surface intact.
# ========================================

start = time.time()

# Create the folders the store the N4bias file
N4Bias_folder=os.path.join(Output_Folder, "S1_N4bias")
PreOP_N4Bias_folder=os.path.join(N4Bias_folder,'Pre_op')
PostOP_N4Bias_folder=os.path.join(N4Bias_folder,'Post_op')

if not os.path.exists(N4Bias_folder):
    os.makedirs(N4Bias_folder)
    os.makedirs(PreOP_N4Bias_folder)
    os.makedirs(PostOP_N4Bias_folder)

Pre_op_N4Bias=ants.n4_bias_field_correction(pre_op_fake)
Pre_op_N4Bias.image_write(PreOP_N4Bias_folder+"/Orig_N4bias.nii.gz",ri=True)

Post_op_N4Bias=ants.n4_bias_field_correction(post_op_fake)
Post_op_N4Bias.image_write(PostOP_N4Bias_folder+"/Orig_N4bias.nii.gz",ri=True)

end = time.time()

recorded_time=end-start
print(recorded_time)

Time_keeping = pd.concat([Time_keeping, pd.DataFrame(['Time_(SEC)',recorded_time])], ignore_index=True)

## ---- 2.2 Run mri_synthstrip ----
# Get mri_synthstrip version of the image - basically with the pial surface still attched, this is so we arnt doing a bet that goes deep within the resection cavity

start = time.time()

print("2.2.1 Pre-op mri_synthstrip")


mri_synthstrip_folder=os.path.join(Output_Folder, "S2_mri_synthstrip")
PreOP_mri_synthstrip_folder=os.path.join(mri_synthstrip_folder,'Pre_op')
PostOP_mri_synthstrip_folder=os.path.join(mri_synthstrip_folder,'Post_op')

if not os.path.exists(mri_synthstrip_folder):
    os.makedirs(mri_synthstrip_folder)
    os.makedirs(PreOP_mri_synthstrip_folder)
    os.makedirs(PostOP_mri_synthstrip_folder)


os.system('python3 ' +mri_synthstrip+ ' -i ' + PreOP_N4Bias_folder+'/Orig_N4bias.nii.gz -o ' + PreOP_mri_synthstrip_folder+'/Orig_N4bias_synthstrip_B1.nii.gz -b 1')

os.system('python3 ' +mri_synthstrip+ ' -i ' + PostOP_N4Bias_folder+'/Orig_N4bias.nii.gz -o ' + PostOP_mri_synthstrip_folder+'/Orig_N4bias_synthstrip_B1.nii.gz -b 1')

end = time.time()

recorded_time=end-start
print(recorded_time)

Time_keeping = pd.concat([Time_keeping, pd.DataFrame(['mri_synthstrip',recorded_time])], ignore_index=True)

## ---- 2.3 Run Synthseg ----
#  SynthSeg is a Deep learning tool for segmentation of brain scans of any contrast - It takes awhile to run but its produces a good segemention of the brain that we will use to group the atlas regions into lobes and additionally have a mask of the brain

start = time.time()

mri_synthseg_folder=os.path.join(Output_Folder, "S3_mri_synthseg")
PreOP_mri_synthseg_folder=os.path.join(mri_synthseg_folder,'Pre_op')
PostOP_mri_synthseg_folder=os.path.join(mri_synthseg_folder,'Post_op')

if not os.path.exists(mri_synthseg_folder):
    os.makedirs(mri_synthseg_folder)
    os.makedirs(PreOP_mri_synthseg_folder)
    os.makedirs(PostOP_mri_synthseg_folder)


os.system('python ' +mri_synthseg+ ' --i ' + PreOP_mri_synthstrip_folder+'/Orig_N4bias_synthstrip_B1.nii.gz  --o ' + PreOP_mri_synthseg_folder+'/PreOP_Sseg.nii.gz --parc')

os.system('python ' +mri_synthseg+ ' --i ' + PostOP_mri_synthstrip_folder+'/Orig_N4bias_synthstrip_B1.nii.gz --o ' + PostOP_mri_synthseg_folder+'/PostOP_Sseg.nii.gz --parc')

end = time.time()

recorded_time=end-start
print(recorded_time)

Time_keeping = pd.concat([Time_keeping, pd.DataFrame(['mri_synthseg',recorded_time])], ignore_index=True)

## ---- 2.4.1 Use the Synthseg to remove pial surface ----

start = time.time()

Skull_strip_folder=os.path.join(Output_Folder, "S4_Skull_strip")
PreOP_Skull_strip_folder=os.path.join(Skull_strip_folder,'Pre_op')
PostOP_Skull_strip_folder=os.path.join(Skull_strip_folder,'Post_op')

if not os.path.exists(Skull_strip_folder):
    os.makedirs(Skull_strip_folder)
    os.makedirs(PreOP_Skull_strip_folder)
    os.makedirs(PostOP_Skull_strip_folder)

#Pre-op
# In the mri_synthseg region 24 relates to areas of CSF that we want to remove from the image

PreOP_Sseg_image = ants.image_read(PreOP_mri_synthseg_folder+'/PreOP_Sseg.nii.gz' )
PreOP_Orig_N4bias_synthstrip_B1 = ants.image_read(PreOP_mri_synthstrip_folder+'/Orig_N4bias_synthstrip_B1.nii.gz' )

# area 24 is the area outside the brain that we dont need
PreOP_Sseg_image_thr_24 = ants.threshold_image( PreOP_Sseg_image, 24, 24 )
PreOP_Sseg_image_thr_24.image_write(PreOP_mri_synthseg_folder+"/PreOP_Sseg_area_24.nii.gz",ri=True)
PreOP_Sseg_MASK = ants.get_mask(PreOP_Sseg_image,low_thresh=1,cleanup=0)
PreOP_Sseg_MASK = PreOP_Sseg_MASK - PreOP_Sseg_image_thr_24
PreOP_Sseg_MASK.image_write(PreOP_mri_synthseg_folder+"/PreOP_Sseg_MASK.nii.gz.nii.gz",ri=True)

PreOP_Orig_N4bias_synthstrip_B1_MUL_Sseg = PreOP_Orig_N4bias_synthstrip_B1 * PreOP_Sseg_MASK
PreOP_Orig_N4bias_synthstrip_B1_MUL_Sseg.image_write(PreOP_Skull_strip_folder+"/Final_skullstriped_image.nii.gz",ri=True)

## ---- 2.4.2 Post-op synthseg - remove pial ----

PostOP_Sseg_image = ants.image_read(PostOP_mri_synthseg_folder+'/PostOP_Sseg.nii.gz' )
PostOP_Orig_N4bias_synthstrip_B1 = ants.image_read(PostOP_mri_synthstrip_folder+'/Orig_N4bias_synthstrip_B1.nii.gz' )

# area 24 is the area outside the brain that we dont need
PostOP_Sseg_image_thr_24 = ants.threshold_image( PostOP_Sseg_image, 24, 24 )
PostOP_Sseg_image_thr_24.image_write(PostOP_mri_synthseg_folder+"/PostOP_Sseg_area_24.nii.gz",ri=True)
PostOP_Sseg_MASK = ants.get_mask(PostOP_Sseg_image,low_thresh=1,cleanup=0)
PostOP_Sseg_MASK = PostOP_Sseg_MASK - PostOP_Sseg_image_thr_24
PostOP_Sseg_MASK.image_write(PostOP_mri_synthseg_folder+"/PreOP_Sseg_MASK.nii.gz",ri=True)

PostOP_Orig_N4bias_synthstrip_B1_MUL_Sseg = PostOP_Orig_N4bias_synthstrip_B1 * PostOP_Sseg_MASK
PostOP_Orig_N4bias_synthstrip_B1_MUL_Sseg.image_write(PostOP_Skull_strip_folder+"/Final_skullstriped_image.nii.gz",ri=True)

end = time.time()

recorded_time=end-start
print(recorded_time)
Time_keeping = pd.concat([Time_keeping, pd.DataFrame(['remove_pial',recorded_time])], ignore_index=True)


PreOP_Sseg_image = ants.image_read(PreOP_mri_synthseg_folder+'/PreOP_Sseg.nii.gz' )
PostOP_Sseg_image = ants.image_read(PostOP_mri_synthseg_folder+'/PostOP_Sseg.nii.gz' )


# ========================================
# 3 - Mask the lobes - Not resected and resected
# We know what lobe the resection has taken place so lets filter the area where the resection can take place to those lobes. To do this we need to group the regions from the segmentation into lobes, then dilate to get the white matter attached to those GM regions.
# ========================================

# Create folders we will store this sections outputs

start = time.time()

Lobe_template_folder=os.path.join(Output_Folder, "S5_Lobe_template")
PreOP_Lobe_template_folder=os.path.join(Lobe_template_folder,'Pre_op')
PostOP_Lobe_template_folder=os.path.join(Lobe_template_folder,'Post_op')

PreOP_Lobe_template_folder_Regions=os.path.join(PreOP_Lobe_template_folder,'Regions')
PreOP_Lobe_template_folder_Lobes=os.path.join(PreOP_Lobe_template_folder,'Lobes')
PreOP_Lobe_template_folder_Dilation=os.path.join(PreOP_Lobe_template_folder,'Dilation')

PostOP_Lobe_template_folder_Regions=os.path.join(PostOP_Lobe_template_folder,'Regions')
PostOP_Lobe_template_folder_Lobes=os.path.join(PostOP_Lobe_template_folder,'Lobes')
PostOP_Lobe_template_folder_Dilation=os.path.join(PostOP_Lobe_template_folder,'Dilation')

if not os.path.exists(Lobe_template_folder):
    os.makedirs(Lobe_template_folder)
    os.makedirs(PreOP_Lobe_template_folder)
    os.makedirs(PostOP_Lobe_template_folder)

    os.makedirs(PreOP_Lobe_template_folder_Regions)
    os.makedirs(PreOP_Lobe_template_folder_Lobes)
    os.makedirs(PreOP_Lobe_template_folder_Dilation)

    os.makedirs(PostOP_Lobe_template_folder_Regions)
    os.makedirs(PostOP_Lobe_template_folder_Lobes)
    os.makedirs(PostOP_Lobe_template_folder_Dilation)

# Pre FRONTAL
threshold = []
#frontal = sum(ants.threshold_image(, threshold, threshold) for threshold in thresholds)
Pre_Left_Frontal =  ants.threshold_image( PreOP_Sseg_image, 1002, 1002 ) + ants.threshold_image( PreOP_Sseg_image, 1003, 1003 )+ ants.threshold_image( PreOP_Sseg_image, 1012, 1012 )+ ants.threshold_image( PreOP_Sseg_image, 1014, 1014 ) + ants.threshold_image( PreOP_Sseg_image, 1017, 1017 ) + ants.threshold_image( PreOP_Sseg_image, 1018, 1018 ) + ants.threshold_image( PreOP_Sseg_image, 1019, 1019 ) + ants.threshold_image( PreOP_Sseg_image, 1020, 1020 ) + ants.threshold_image( PreOP_Sseg_image, 1024, 1024 ) + ants.threshold_image( PreOP_Sseg_image, 1026, 1026 ) + ants.threshold_image( PreOP_Sseg_image, 1027, 1027 ) + ants.threshold_image( PreOP_Sseg_image, 1028, 1028 ) + ants.threshold_image( PreOP_Sseg_image, 1032, 1032 )
Pre_Left_Frontal = ants.get_mask(Pre_Left_Frontal,low_thresh=1,cleanup=0) * 11
Pre_Left_Frontal.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_Left_Frontal.nii.gz",ri=True)

Pre_Right_Frontal = ants.threshold_image( PreOP_Sseg_image, 2002, 2002 )+ ants.threshold_image( PreOP_Sseg_image, 2003, 2003 )+ ants.threshold_image( PreOP_Sseg_image, 2012, 2012 )+ ants.threshold_image( PreOP_Sseg_image, 2014, 2014 )+ ants.threshold_image( PreOP_Sseg_image, 2017, 2017 )+ ants.threshold_image( PreOP_Sseg_image, 2018, 2018 )+ ants.threshold_image( PreOP_Sseg_image, 2019, 2019 )+ ants.threshold_image( PreOP_Sseg_image, 2020, 2020 )+ ants.threshold_image( PreOP_Sseg_image, 2024, 2024 )+ ants.threshold_image( PreOP_Sseg_image, 2026, 2026 )+ ants.threshold_image( PreOP_Sseg_image, 2027, 2027 )+ ants.threshold_image( PreOP_Sseg_image, 2028, 2028 )+ ants.threshold_image( PreOP_Sseg_image, 2032, 2032 )
Pre_Right_Frontal = ants.get_mask(Pre_Right_Frontal,low_thresh=1,cleanup=0) * 21
Pre_Right_Frontal.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_Right_Frontal.nii.gz",ri=True)

Post_Left_Frontal = ants.threshold_image( PostOP_Sseg_image, 1002, 1002 ) + ants.threshold_image( PostOP_Sseg_image, 1003, 1003 ) + ants.threshold_image( PostOP_Sseg_image, 1012, 1012 ) + ants.threshold_image( PostOP_Sseg_image, 1014, 1014 ) + ants.threshold_image( PostOP_Sseg_image, 1017, 1017 ) + ants.threshold_image( PostOP_Sseg_image, 1018, 1018 ) + ants.threshold_image( PostOP_Sseg_image, 1019, 1019 ) + ants.threshold_image( PostOP_Sseg_image, 1020, 1020 ) + ants.threshold_image( PostOP_Sseg_image, 1024, 1024 ) + ants.threshold_image( PostOP_Sseg_image, 1026, 1026 ) + ants.threshold_image( PostOP_Sseg_image, 1027, 1027 ) + ants.threshold_image( PostOP_Sseg_image, 1028, 1028 ) + ants.threshold_image( PostOP_Sseg_image, 1032, 1032 )
Post_Left_Frontal = ants.get_mask(Post_Left_Frontal,low_thresh=1,cleanup=0) * 11
Post_Left_Frontal.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_Left_Frontal.nii.gz",ri=True)

Post_Right_Frontal =  ants.threshold_image( PostOP_Sseg_image, 2002, 2002 ) + ants.threshold_image( PostOP_Sseg_image, 2003, 2003 ) + ants.threshold_image( PostOP_Sseg_image, 2012, 2012 ) + ants.threshold_image( PostOP_Sseg_image, 2014, 2014 ) + ants.threshold_image( PostOP_Sseg_image, 2017, 2017 ) + ants.threshold_image( PostOP_Sseg_image, 2018, 2018 ) + ants.threshold_image( PostOP_Sseg_image, 2019, 2019 ) + ants.threshold_image( PostOP_Sseg_image, 2020, 2020 ) + ants.threshold_image( PostOP_Sseg_image, 2024, 2024 ) + ants.threshold_image( PostOP_Sseg_image, 2026, 2026 ) + ants.threshold_image( PostOP_Sseg_image, 2027, 2027 ) + ants.threshold_image( PostOP_Sseg_image, 2028, 2028 ) + ants.threshold_image( PostOP_Sseg_image, 2032, 2032 )
Post_Right_Frontal = ants.get_mask(Post_Right_Frontal,low_thresh=1,cleanup=0) * 21
Post_Right_Frontal.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_Right_Frontal.nii.gz",ri=True)

Pre_Left_Parietal = ants.threshold_image( PreOP_Sseg_image, 1008, 1008 ) + ants.threshold_image( PreOP_Sseg_image, 1010, 1010 ) + ants.threshold_image( PreOP_Sseg_image, 1022, 1022 ) + ants.threshold_image( PreOP_Sseg_image, 1023, 1023 ) + ants.threshold_image( PreOP_Sseg_image, 1029, 1029 ) + ants.threshold_image( PreOP_Sseg_image, 1031, 1031 )
Pre_Left_Parietal = ants.get_mask(Pre_Left_Parietal,low_thresh=1,cleanup=0) * 12
Pre_Left_Parietal.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_Left_Parietal.nii.gz",ri=True)

Pre_Right_Parietal = ants.threshold_image( PreOP_Sseg_image, 2008, 2008 ) + ants.threshold_image( PreOP_Sseg_image, 2010, 2010 ) + ants.threshold_image( PreOP_Sseg_image, 2022, 2022 ) + ants.threshold_image( PreOP_Sseg_image, 2023, 2023 ) + ants.threshold_image( PreOP_Sseg_image, 2029, 2029 ) + ants.threshold_image( PreOP_Sseg_image, 2031, 2031 )
Pre_Right_Parietal = ants.get_mask(Pre_Right_Parietal,low_thresh=1,cleanup=0) * 22
Pre_Right_Parietal.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_Right_Parietal.nii.gz",ri=True)

Post_Left_Parietal = ants.threshold_image( PostOP_Sseg_image, 1008, 1008 ) + ants.threshold_image( PostOP_Sseg_image, 1010, 1010 ) + ants.threshold_image( PostOP_Sseg_image, 1022, 1022 ) + ants.threshold_image( PostOP_Sseg_image, 1023, 1023 ) + ants.threshold_image( PostOP_Sseg_image, 1029, 1029 ) + ants.threshold_image( PostOP_Sseg_image, 1031, 1031 )
Post_Left_Parietal = ants.get_mask(Post_Left_Parietal,low_thresh=1,cleanup=0) * 12
Post_Left_Parietal.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_Left_Parietal.nii.gz",ri=True)

Post_Right_Parietal = ants.threshold_image( PostOP_Sseg_image, 2008, 2008 ) + ants.threshold_image( PostOP_Sseg_image, 2010, 2010 ) + ants.threshold_image( PostOP_Sseg_image, 2022, 2022 ) + ants.threshold_image( PostOP_Sseg_image, 2023, 2023 ) + ants.threshold_image( PostOP_Sseg_image, 2029, 2029 ) + ants.threshold_image( PostOP_Sseg_image, 2031, 2031 )
Post_Right_Parietal = ants.get_mask(Post_Right_Parietal,low_thresh=1,cleanup=0) * 22
Post_Right_Parietal.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_Right_Parietal.nii.gz",ri=True)


Pre_Left_Temporal = ants.threshold_image( PreOP_Sseg_image, 1001, 1001 ) + ants.threshold_image( PreOP_Sseg_image, 1006, 1006 ) + ants.threshold_image( PreOP_Sseg_image, 1007, 1007 ) + ants.threshold_image( PreOP_Sseg_image, 1009, 1009 ) + ants.threshold_image( PreOP_Sseg_image, 1015, 1015 ) + ants.threshold_image( PreOP_Sseg_image, 1016, 1016 ) + ants.threshold_image( PreOP_Sseg_image, 1030, 1030 ) + ants.threshold_image( PreOP_Sseg_image, 1033, 1033 ) + ants.threshold_image( PreOP_Sseg_image, 1034, 1034 )
Pre_Left_Temporal = ants.get_mask(Pre_Left_Temporal,low_thresh=1,cleanup=0) * 13
Pre_Left_Temporal.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_Left_Temporal.nii.gz",ri=True)

Pre_Right_Temporal = ants.threshold_image( PreOP_Sseg_image, 2001, 2001 ) + ants.threshold_image( PreOP_Sseg_image, 2006, 2006 ) + ants.threshold_image( PreOP_Sseg_image, 2007, 2007 ) + ants.threshold_image( PreOP_Sseg_image, 2009, 2009 ) + ants.threshold_image( PreOP_Sseg_image, 2015, 2015 ) + ants.threshold_image( PreOP_Sseg_image, 2016, 2016 ) + ants.threshold_image( PreOP_Sseg_image, 2030, 2030 ) + ants.threshold_image( PreOP_Sseg_image, 2033, 2033 ) + ants.threshold_image( PreOP_Sseg_image, 2034, 2034 )
Pre_Right_Temporal = ants.get_mask(Pre_Right_Temporal,low_thresh=1,cleanup=0) * 23
Pre_Right_Temporal.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_Right_Temporal.nii.gz",ri=True)

Post_Left_Temporal =  ants.threshold_image( PostOP_Sseg_image, 1001, 1001 ) +  ants.threshold_image( PostOP_Sseg_image, 1006, 1006 ) +  ants.threshold_image( PostOP_Sseg_image, 1007, 1007 ) + ants.threshold_image( PostOP_Sseg_image, 1009, 1009 ) +  ants.threshold_image( PostOP_Sseg_image, 1015, 1015 ) + ants.threshold_image( PostOP_Sseg_image, 1016, 1016 ) + ants.threshold_image( PostOP_Sseg_image, 1030, 1030 ) + ants.threshold_image( PostOP_Sseg_image, 1033, 1033 ) + ants.threshold_image( PostOP_Sseg_image, 1034, 1034 )
Post_Left_Temporal = ants.get_mask(Post_Left_Temporal,low_thresh=1,cleanup=0) * 13
Post_Left_Temporal.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_Left_Temporal.nii.gz",ri=True)

Post_Right_Temporal = ants.threshold_image( PostOP_Sseg_image, 2001, 2001 ) + ants.threshold_image( PostOP_Sseg_image, 2006, 2006 ) +  ants.threshold_image( PostOP_Sseg_image, 2007, 2007 ) +  ants.threshold_image( PostOP_Sseg_image, 2009, 2009 ) +  ants.threshold_image( PostOP_Sseg_image, 2015, 2015 ) +  ants.threshold_image( PostOP_Sseg_image, 2016, 2016 ) + ants.threshold_image( PostOP_Sseg_image, 2030, 2030 ) + ants.threshold_image( PostOP_Sseg_image, 2033, 2033 ) + ants.threshold_image( PostOP_Sseg_image, 2034, 2034 )
Post_Right_Temporal = ants.get_mask(Post_Right_Temporal,low_thresh=1,cleanup=0) * 23
Post_Right_Temporal.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_Right_Temporal.nii.gz",ri=True)

Pre_Left_Occipital = ants.threshold_image( PreOP_Sseg_image, 1005, 1005 ) + ants.threshold_image( PreOP_Sseg_image, 1011, 1011 ) + ants.threshold_image( PreOP_Sseg_image, 1013, 1013 ) + ants.threshold_image( PreOP_Sseg_image, 1021, 1021 ) + ants.threshold_image( PreOP_Sseg_image, 1025, 1025 )
Pre_Left_Occipital = ants.get_mask(Pre_Left_Occipital,low_thresh=1,cleanup=0) * 14
Pre_Left_Occipital.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_Left_Occipital.nii.gz",ri=True)

Pre_Right_Occipital = ants.threshold_image( PreOP_Sseg_image, 2005, 2005 ) + ants.threshold_image( PreOP_Sseg_image, 2011, 2011 ) + ants.threshold_image( PreOP_Sseg_image, 2013, 2013 ) + ants.threshold_image( PreOP_Sseg_image, 2021, 2021 ) + ants.threshold_image( PreOP_Sseg_image, 2025, 2025 )
Pre_Right_Occipital = ants.get_mask(Pre_Right_Occipital,low_thresh=1,cleanup=0) * 24
Pre_Right_Occipital.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_Right_Occipital.nii.gz",ri=True)

Post_Left_Occipital = ants.threshold_image( PostOP_Sseg_image, 1005, 1005 ) + ants.threshold_image( PostOP_Sseg_image, 1011, 1011 ) + ants.threshold_image( PostOP_Sseg_image, 1013, 1013 ) + ants.threshold_image( PostOP_Sseg_image, 1021, 1021 ) + ants.threshold_image( PostOP_Sseg_image, 1025, 1025 )
Post_Left_Occipital = ants.get_mask(Post_Left_Occipital,low_thresh=1,cleanup=0) * 14
Post_Left_Occipital.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_Left_Occipital.nii.gz",ri=True)

Post_Right_Occipital = ants.threshold_image( PostOP_Sseg_image, 2005, 2005 ) + ants.threshold_image( PostOP_Sseg_image, 2011, 2011 ) + ants.threshold_image( PostOP_Sseg_image, 2013, 2013 ) + ants.threshold_image( PostOP_Sseg_image, 2021, 2021 ) + ants.threshold_image( PostOP_Sseg_image, 2025, 2025 )
Post_Right_Occipital = ants.get_mask(Post_Right_Occipital,low_thresh=1,cleanup=0) * 24
Post_Right_Occipital.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_Right_Occipital.nii.gz",ri=True)

Pre_Left_Insula = ants.threshold_image( PreOP_Sseg_image, 1035, 1035 )
Pre_Left_Insula = ants.get_mask(Pre_Left_Insula,low_thresh=1,cleanup=0) * 15
Pre_Left_Insula.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_Left_Insula.nii.gz",ri=True)

Pre_Right_Insula = ants.threshold_image( PreOP_Sseg_image, 2035, 2035 )
Pre_Right_Insula = ants.get_mask(Pre_Right_Insula,low_thresh=1,cleanup=0) * 25
Pre_Right_Insula.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_Right_Insula.nii.gz",ri=True)

Post_Left_Insula = ants.threshold_image( PostOP_Sseg_image, 1035, 1035 )
Post_Left_Insula = ants.get_mask(Post_Left_Insula,low_thresh=1,cleanup=0) * 15
Post_Left_Insula.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_Left_Insula.nii.gz",ri=True)

Post_Right_Insula = ants.threshold_image( PostOP_Sseg_image, 2035, 2035 )
Post_Right_Insula = ants.get_mask(Post_Right_Insula,low_thresh=1,cleanup=0) * 25
Post_Right_Insula.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_Right_Insula.nii.gz",ri=True)


Pre_left_Sub_Cortical = ants.threshold_image( PreOP_Sseg_image, 10, 10 ) + ants.threshold_image( PreOP_Sseg_image, 11, 11 ) +  ants.threshold_image( PreOP_Sseg_image, 12, 12 ) +  ants.threshold_image( PreOP_Sseg_image, 13, 13 ) +  ants.threshold_image( PreOP_Sseg_image, 17, 17 ) +  ants.threshold_image( PreOP_Sseg_image, 18, 18 ) +  ants.threshold_image( PreOP_Sseg_image, 26, 26 ) +  ants.threshold_image( PreOP_Sseg_image, 28, 28 )
Pre_left_Sub_Cortical = ants.get_mask(Pre_left_Sub_Cortical,low_thresh=1,cleanup=0) * 16
Pre_left_Sub_Cortical.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_left_Sub_Cortical.nii.gz",ri=True)

Pre_right_Sub_Cortical = ants.threshold_image( PreOP_Sseg_image, 49, 49 ) + ants.threshold_image( PreOP_Sseg_image, 50, 50 ) + ants.threshold_image( PreOP_Sseg_image, 51, 51 ) + ants.threshold_image( PreOP_Sseg_image, 52, 52 ) + ants.threshold_image( PreOP_Sseg_image, 53, 53 ) + ants.threshold_image( PreOP_Sseg_image, 54, 54 ) +  ants.threshold_image( PreOP_Sseg_image, 58, 58 ) + ants.threshold_image( PreOP_Sseg_image, 60, 60 )
Pre_right_Sub_Cortical = ants.get_mask(Pre_right_Sub_Cortical,low_thresh=1,cleanup=0) * 26
Pre_right_Sub_Cortical.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_right_Sub_Cortical.nii.gz",ri=True)

Post_left_Sub_Cortical = ants.threshold_image( PostOP_Sseg_image, 10, 10 ) + ants.threshold_image( PostOP_Sseg_image, 11, 11 ) + ants.threshold_image( PostOP_Sseg_image, 12, 12 ) + ants.threshold_image( PostOP_Sseg_image, 13, 13 ) + ants.threshold_image( PostOP_Sseg_image, 17, 17 ) + ants.threshold_image( PostOP_Sseg_image, 18, 18 ) + ants.threshold_image( PostOP_Sseg_image, 26, 26 ) +  ants.threshold_image( PostOP_Sseg_image, 28, 28 )
Post_left_Sub_Cortical = ants.get_mask(Post_left_Sub_Cortical,low_thresh=1,cleanup=0) * 16
Post_left_Sub_Cortical.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_left_Sub_Cortical.nii.gz",ri=True)

Post_right_Sub_Cortical = ants.threshold_image( PostOP_Sseg_image, 49, 49 ) + ants.threshold_image( PostOP_Sseg_image, 50, 50 ) + ants.threshold_image( PostOP_Sseg_image, 51, 51 ) + ants.threshold_image( PostOP_Sseg_image, 52, 52 ) + ants.threshold_image( PostOP_Sseg_image, 53, 53 ) + ants.threshold_image( PostOP_Sseg_image, 54, 54 ) + ants.threshold_image( PostOP_Sseg_image, 58, 58 ) + ants.threshold_image( PostOP_Sseg_image, 60, 60 )
Post_right_Sub_Cortical = ants.get_mask(Post_right_Sub_Cortical,low_thresh=1,cleanup=0) * 26
Post_right_Sub_Cortical.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_right_Sub_Cortical.nii.gz",ri=True)


Pre_NO_GO = ants.threshold_image( PreOP_Sseg_image, 4, 4 ) + ants.threshold_image( PreOP_Sseg_image, 7, 7 ) + ants.threshold_image( PreOP_Sseg_image, 8, 8 ) + ants.threshold_image( PreOP_Sseg_image, 14, 14 ) + ants.threshold_image( PreOP_Sseg_image, 15, 15 ) + ants.threshold_image( PreOP_Sseg_image, 16, 16 ) + ants.threshold_image( PreOP_Sseg_image, 43, 43 ) + ants.threshold_image( PreOP_Sseg_image, 46, 46 ) + ants.threshold_image( PreOP_Sseg_image, 47, 47 )
Pre_NO_GO = ants.get_mask(Pre_NO_GO,low_thresh=1,cleanup=0) * 50
Pre_NO_GO.image_write(PreOP_Lobe_template_folder_Lobes+"/Pre_NO_GO.nii.gz",ri=True)

Post_NO_GO = ants.threshold_image( PostOP_Sseg_image, 4, 4 ) + ants.threshold_image( PostOP_Sseg_image, 7, 7 ) + ants.threshold_image( PostOP_Sseg_image, 8, 8 ) + ants.threshold_image( PostOP_Sseg_image, 14, 14 ) + ants.threshold_image( PostOP_Sseg_image, 15, 15 ) + ants.threshold_image( PostOP_Sseg_image, 16, 16 ) + ants.threshold_image( PostOP_Sseg_image, 43, 43 ) + ants.threshold_image( PostOP_Sseg_image, 46, 46 ) + ants.threshold_image( PostOP_Sseg_image, 47, 47 )
Post_NO_GO = ants.get_mask(Post_NO_GO,low_thresh=1,cleanup=0) * 50
Post_NO_GO.image_write(PostOP_Lobe_template_folder_Lobes+"/Post_NO_GO.nii.gz",ri=True)

# ========================================
# 3 - Mask the lobes - Not resected and resected
# We know what lobe the resection has taken place so lets filter the area where the resection can take place to those lobes. To do this we need to group the regions from the segmentation into lobes, then dilate to get the white matter attached to those GM regions.
# ========================================

# Create folders we will store this sections outputs

start = time.time()

Lobe_template_folder=os.path.join(Output_Folder, "S5_Lobe_template")
PreOP_Lobe_template_folder=os.path.join(Lobe_template_folder,'Pre_op')
PostOP_Lobe_template_folder=os.path.join(Lobe_template_folder,'Post_op')

PreOP_Lobe_template_folder_Regions=os.path.join(PreOP_Lobe_template_folder,'Regions')
PreOP_Lobe_template_folder_Lobes=os.path.join(PreOP_Lobe_template_folder,'Lobes')
PreOP_Lobe_template_folder_Dilation=os.path.join(PreOP_Lobe_template_folder,'Dilation')

PostOP_Lobe_template_folder_Regions=os.path.join(PostOP_Lobe_template_folder,'Regions')
PostOP_Lobe_template_folder_Lobes=os.path.join(PostOP_Lobe_template_folder,'Lobes')
PostOP_Lobe_template_folder_Dilation=os.path.join(PostOP_Lobe_template_folder,'Dilation')

if not os.path.exists(Lobe_template_folder):
    os.makedirs(Lobe_template_folder)
    os.makedirs(PreOP_Lobe_template_folder)
    os.makedirs(PostOP_Lobe_template_folder)

    os.makedirs(PreOP_Lobe_template_folder_Regions)
    os.makedirs(PreOP_Lobe_template_folder_Lobes)
    os.makedirs(PreOP_Lobe_template_folder_Dilation)

    os.makedirs(PostOP_Lobe_template_folder_Regions)
    os.makedirs(PostOP_Lobe_template_folder_Lobes)
    os.makedirs(PostOP_Lobe_template_folder_Dilation)

# "-- 3.3.8 Combind-Image --"
PreOP_Lobe_Atlas = Pre_Left_Frontal + Pre_Right_Frontal + Pre_Left_Parietal + Pre_Right_Parietal + Pre_Left_Temporal + Pre_Right_Temporal + Pre_Left_Occipital + Pre_Right_Occipital + Pre_Left_Insula + Pre_Right_Insula + Pre_left_Sub_Cortical + Pre_right_Sub_Cortical + Pre_NO_GO
PreOP_Lobe_Atlas.image_write(PreOP_Lobe_template_folder_Lobes+"/PreOP_Lobe_Atlas.nii.gz",ri=True)

PreOP_Lobe_Atlas_WITHOUT_NG = Pre_Left_Frontal + Pre_Right_Frontal + Pre_Left_Parietal + Pre_Right_Parietal + Pre_Left_Temporal + Pre_Right_Temporal + Pre_Left_Occipital + Pre_Right_Occipital + Pre_Left_Insula + Pre_Right_Insula + Pre_left_Sub_Cortical + Pre_right_Sub_Cortical
PreOP_Lobe_Atlas_WITHOUT_NG.image_write(PreOP_Lobe_template_folder_Lobes+"/PreOP_Lobe_Atlas_Without_NG.nii.gz",ri=True)


PostOP_Lobe_Atlas = Post_Left_Frontal + Post_Right_Frontal + Post_Left_Parietal + Post_Right_Parietal + Post_Left_Temporal + Post_Right_Temporal + Post_Left_Occipital + Post_Right_Occipital + Post_Left_Insula + Post_Right_Insula + Post_left_Sub_Cortical + Post_right_Sub_Cortical + Post_NO_GO
PostOP_Lobe_Atlas.image_write(PostOP_Lobe_template_folder_Lobes+"/PostOP_Lobe_Atlas.nii.gz",ri=True)

PostOP_Lobe_Atlas_WITHOUT_NG = Post_Left_Frontal + Post_Right_Frontal + Post_Left_Parietal + Post_Right_Parietal + Post_Left_Temporal + Post_Right_Temporal + Post_Left_Occipital + Post_Right_Occipital + Post_Left_Insula + Post_Right_Insula + Post_left_Sub_Cortical + Post_right_Sub_Cortical
PostOP_Lobe_Atlas_WITHOUT_NG.image_write(PreOP_Lobe_template_folder_Lobes+"/PostOP_Lobe_Atlas_Without_NG.nii.gz",ri=True)

end = time.time()

recorded_time=end-start
print(recorded_time)
Time_keeping = pd.concat([Time_keeping, pd.DataFrame(['Group_lobes',recorded_time])], ignore_index=True)

# "---- 3.4 Dilation-Image ----"

PRE_Lobe_dilation_img_data = nib.load(PreOP_Lobe_template_folder_Lobes+"/PreOP_Lobe_Atlas_Without_NG.nii.gz")
PRE_Lobe_dilation_img = PRE_Lobe_dilation_img_data.get_fdata()
PRE_Lobe_dilation_img[PRE_Lobe_dilation_img==0] = np.nan

invalid=None
if invalid is None: invalid = np.isnan(PRE_Lobe_dilation_img)
idx = nd.distance_transform_edt(invalid, return_distances=False, return_indices=True)
PRE_Lobe_dilation_img = PRE_Lobe_dilation_img[tuple(idx)]

PRE_save = nib.Nifti1Image(PRE_Lobe_dilation_img,PRE_Lobe_dilation_img_data.affine,PRE_Lobe_dilation_img_data.header)
nib.save(PRE_save,PreOP_Lobe_template_folder_Dilation+"/PreOP_ATLAS_DIL.nii.gz")

PreOP_ATLAS_DIL = ants.image_read(PreOP_Lobe_template_folder_Dilation+"/PreOP_ATLAS_DIL.nii.gz" )

Pre_NO_GO_Mask = ants.get_mask(Pre_NO_GO,low_thresh=1,cleanup=0) * 1

PreOP_ATLAS_DIL_NO_GO = PreOP_ATLAS_DIL * Pre_NO_GO_Mask
PreOP_ATLAS_DIL = PreOP_ATLAS_DIL - PreOP_ATLAS_DIL_NO_GO
PreOP_ATLAS_DIL = PreOP_ATLAS_DIL + Pre_NO_GO
PreOP_ATLAS_DIL.image_write(PreOP_Lobe_template_folder_Dilation+"/PreOP_ATLAS_DIL.nii.gz",ri=True)


POST_Lobe_dilation_img_data = nib.load(PreOP_Lobe_template_folder_Lobes+"/PostOP_Lobe_Atlas_Without_NG.nii.gz")
POST_Lobe_dilation_img = POST_Lobe_dilation_img_data.get_fdata()
POST_Lobe_dilation_img[POST_Lobe_dilation_img==0] = np.nan

invalid=None
if invalid is None: invalid = np.isnan(POST_Lobe_dilation_img)
idx = nd.distance_transform_edt(invalid, return_distances=False, return_indices=True)
POST_Lobe_dilation_img = POST_Lobe_dilation_img[tuple(idx)]

POST_save = nib.Nifti1Image(POST_Lobe_dilation_img,POST_Lobe_dilation_img_data.affine,POST_Lobe_dilation_img_data.header)
nib.save(POST_save,PostOP_Lobe_template_folder_Dilation+"/PostOP_ATLAS_DIL.nii.gz")

PostOP_ATLAS_DIL = ants.image_read(PostOP_Lobe_template_folder_Dilation+"/PostOP_ATLAS_DIL.nii.gz" )

Post_NO_GO_Mask = ants.get_mask(Post_NO_GO,low_thresh=1,cleanup=0) * 1

PostOP_ATLAS_DIL_NO_GO = PostOP_ATLAS_DIL * Post_NO_GO_Mask
PostOP_ATLAS_DIL = PostOP_ATLAS_DIL - PostOP_ATLAS_DIL_NO_GO
PostOP_ATLAS_DIL = PostOP_ATLAS_DIL + Post_NO_GO
PostOP_ATLAS_DIL.image_write(PostOP_Lobe_template_folder_Dilation+"/PostOP_ATLAS_DIL.nii.gz",ri=True)

PreOP_ATLAS_DIL = ants.image_read(PreOP_Lobe_template_folder_Dilation+"/PreOP_ATLAS_DIL.nii.gz" )
PostOP_ATLAS_DIL = ants.image_read(PostOP_Lobe_template_folder_Dilation+"/PostOP_ATLAS_DIL.nii.gz" )

PreOP_ATLAS_DIL_FILTER = PreOP_ATLAS_DIL * PreOP_Sseg_MASK

PostOP_ATLAS_DIL_FILTER = PostOP_ATLAS_DIL * PostOP_Sseg_MASK

PreOP_ATLAS_DIL_FILTER.image_write(PreOP_Lobe_template_folder_Dilation+"/PreOP_ATLAS_DIL_FILTER.nii.gz",ri=True)
PostOP_ATLAS_DIL_FILTER.image_write(PostOP_Lobe_template_folder_Dilation+"/PostOP_ATLAS_DIL_FILTER.nii.gz",ri=True)

# echo "---- 3.5 Get the lobes where the resection took places ----"
# as we have a mask for each of the lobes lets make 2 new mask for each image
# feild_map_Resected_area which is a mask of all lobes a user specifies the resection takes place
# feild_map_NONE_Resected_area which is the lobes where resection didnt take place

start = time.time()

Lobe_of_resection=os.path.join(Output_Folder, "S6_Lobe_of_resection")

if not os.path.exists(Lobe_of_resection):
    os.makedirs(Lobe_of_resection)

Pre_OP_feild_map_Resected_area = ants.get_mask(PreOP_Lobe_Atlas,low_thresh=1,cleanup=0) * 0
Post_OP_feild_map_Resected_area = ants.get_mask(PostOP_Lobe_Atlas,low_thresh=1,cleanup=0) * 0

# What key is each lobe attched too
Frontal="F"
Parietal="P"
Temporal="T"
Occipital="O"
Insula="I"

# Pre-op
if Hemisphere == "L":
    print("Hemisphere is Left")

    if Temporal in Lobe:
        print("Temporal")

        PreOP_Left_Temporal = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 13, 13 )
        PreOP_Left_Sub = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 15, 15 )
        PreOP_Left_Insula = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 16, 16 )
        
        Pre_OP_feild_map_Resected_area = Post_OP_feild_map_Resected_area + PreOP_Left_Temporal + PreOP_Left_Sub + PreOP_Left_Insula
        Pre_OP_feild_map_Resected_area = ants.get_mask(Pre_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1
        
        PostOP_Left_Temporal = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 13, 13 )
        PostOP_Left_Sub = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 15, 15 )
        PostOP_Left_Insula = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 16, 16 )
        
        Post_OP_feild_map_Resected_area = Post_OP_feild_map_Resected_area + PostOP_Left_Temporal + PostOP_Left_Sub + PostOP_Left_Insula
        Post_OP_feild_map_Resected_area = ants.get_mask(Post_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1
    
    if Frontal in Lobe:
        print("Frontal")

        PreOP_Left_Frontal = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 11, 11 )

        Pre_OP_feild_map_Resected_area = Pre_OP_feild_map_Resected_area + PreOP_Left_Frontal
        Pre_OP_feild_map_Resected_area = ants.get_mask(Pre_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1

        
        PostOP_Left_Frontal = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 11, 11 )

        Post_OP_feild_map_Resected_area = Post_OP_feild_map_Resected_area + PostOP_Left_Frontal
        Post_OP_feild_map_Resected_area = ants.get_mask(Post_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1
      
    if Parietal in Lobe:
        print("Parietal")

        PreOP_Left_Parietal = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 12, 12 )
        Pre_OP_feild_map_Resected_area = Pre_OP_feild_map_Resected_area + PreOP_Left_Parietal
        Pre_OP_feild_map_Resected_area = ants.get_mask(Pre_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1

        PostOP_Left_Parietal = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 12, 12 )
        Post_OP_feild_map_Resected_area = Post_OP_feild_map_Resected_area + PostOP_Left_Parietal
        Post_OP_feild_map_Resected_area = ants.get_mask(Post_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1
    
    if Occipital in Lobe:
        print("Occipital")

        PreOP_Left_Occipital = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 14, 14 )
        Pre_OP_feild_map_Resected_area = Pre_OP_feild_map_Resected_area + PreOP_Left_Occipital
        Pre_OP_feild_map_Resected_area = ants.get_mask(Pre_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1
    
        PostOP_Left_Occipital = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 14, 14 )
        Post_OP_feild_map_Resected_area = Post_OP_feild_map_Resected_area + PostOP_Left_Occipital
        Post_OP_feild_map_Resected_area = ants.get_mask(Post_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1
    
    if Insula in Lobe:
        print("Insula")

        PreOP_Left_Insula = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 15, 15 )
        Pre_OP_feild_map_Resected_area = Pre_OP_feild_map_Resected_area + PreOP_Left_Insula
        Pre_OP_feild_map_Resected_area = ants.get_mask(Pre_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1

        PostOP_Left_Insula = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 15, 15 )
        Post_OP_feild_map_Resected_area = Post_OP_feild_map_Resected_area + PostOP_Left_Insula
        Post_OP_feild_map_Resected_area = ants.get_mask(Post_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1
  

elif Hemisphere == "R":
    print("Hemisphere is Right")

    if Temporal in Lobe:
        print("Temporal")


        PreOP_Right_Temporal = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 23, 23 )
        PreOP_Right_Sub = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 25, 25 )
        PreOP_Right_Insula = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 26, 26 )
        
        Pre_OP_feild_map_Resected_area = PreOP_Right_Temporal + PreOP_Right_Sub + PreOP_Right_Insula
        Pre_OP_feild_map_Resected_area = ants.get_mask(Pre_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1

        
        PostOP_Right_Temporal = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 23, 23 )
        PostOP_Right_Sub = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 25, 25 )
        PostOP_Right_Insula = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 26, 26 )
        
        Post_OP_feild_map_Resected_area = Post_OP_feild_map_Resected_area + PostOP_Right_Temporal + PostOP_Right_Sub + PostOP_Right_Insula
        Post_OP_feild_map_Resected_area = ants.get_mask(Post_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1

    
    if Frontal in Lobe:
        print("Frontal")

        PreOP_Right_Frontal  = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 21, 21 )

        Pre_OP_feild_map_Resected_area = Pre_OP_feild_map_Resected_area + PreOP_Right_Frontal
        Pre_OP_feild_map_Resected_area = ants.get_mask(Pre_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1

        PostOP_Right_Frontal  = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 21, 21 )

        Post_OP_feild_map_Resected_area = Post_OP_feild_map_Resected_area + PostOP_Right_Frontal
        Post_OP_feild_map_Resected_area = ants.get_mask(Post_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1
      
    
    if Parietal in Lobe:
        print("Parietal")

        PreOP_Right_Parietal = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 22, 22 )
        
        Pre_OP_feild_map_Resected_area = Pre_OP_feild_map_Resected_area + PreOP_Right_Parietal
        Pre_OP_feild_map_Resected_area = ants.get_mask(Pre_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1

        PostOP_Right_Parietal = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 22, 22 )
        
        Post_OP_feild_map_Resected_area = Post_OP_feild_map_Resected_area + PostOP_Right_Parietal
        Post_OP_feild_map_Resected_area = ants.get_mask(Post_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1
  
    
    if Occipital in Lobe:
        print("Occipital")

        PreOP_Right_Occipital = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 24, 24 )
        
        Pre_OP_feild_map_Resected_area = Pre_OP_feild_map_Resected_area + PreOP_Right_Occipital
        Pre_OP_feild_map_Resected_area = ants.get_mask(Pre_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1

        
        PostOP_Right_Occipital = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 24, 24 )
        
        Post_OP_feild_map_Resected_area = Post_OP_feild_map_Resected_area + PostOP_Right_Occipital
        Post_OP_feild_map_Resected_area = ants.get_mask(Post_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1

    if Insula in Lobe:
        print("Insula")

        PreOP_Right_Insula = ants.threshold_image( PreOP_ATLAS_DIL_FILTER, 25, 25 )
        
        Pre_OP_feild_map_Resected_area = Pre_OP_feild_map_Resected_area + PreOP_Right_Insula
        Pre_OP_feild_map_Resected_area = ants.get_mask(Pre_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1

        PostOP_Right_Insula = ants.threshold_image( PostOP_ATLAS_DIL_FILTER, 25, 25 )
        
        Post_OP_feild_map_Resected_area = Post_OP_feild_map_Resected_area + PostOP_Right_Insula
        Post_OP_feild_map_Resected_area = ants.get_mask(Post_OP_feild_map_Resected_area,low_thresh=1,cleanup=0) * 1

# the aim of this for loop is to filter through each of lobes the user specified the resection took place and add add that lobe to the Pre_OP_feild_map
# echo " -- Pre-OP "
# If the hemisphere specified is the left one

Pre_OP_feild_map_Resected_area.image_write(Lobe_of_resection+"/PreOP_feildResection.nii.gz",ri=True)
Post_OP_feild_map_Resected_area.image_write(Lobe_of_resection+"/PostOP_feildResection.nii.gz",ri=True)

PRE_the_none_resected_lobe = Pre_OP_feild_map_Resected_area + PreOP_Sseg_MASK
PRE_the_none_resected_lobe = ants.threshold_image( PRE_the_none_resected_lobe, 1, 1 )

POST_the_none_resected_lobe = Post_OP_feild_map_Resected_area + PostOP_Sseg_MASK
POST_the_none_resected_lobe = ants.threshold_image( POST_the_none_resected_lobe, 1, 1 )

PRE_the_none_resected_lobe.image_write(Lobe_of_resection+"/PreOP_NONE_feildResection.nii.gz",ri=True)
POST_the_none_resected_lobe.image_write(Lobe_of_resection+"/PostOP_NONE_feildResection.nii.gz",ri=True)

end = time.time()

recorded_time=end-start
print(recorded_time)
Time_keeping = pd.concat([Time_keeping, pd.DataFrame(['The_resection_Lobe_mask',recorded_time])], ignore_index=True)

# echo "---- 4.6 Get the Vents ----"

start = time.time()

Get_ventricles=os.path.join(Output_Folder, "S7_Get_ventricles")

if not os.path.exists(Get_ventricles):
    os.makedirs(Get_ventricles)

# PreOP
PreOP_Sseg_image_thr_43 = ants.threshold_image( PreOP_Sseg_image, 43, 43 )
PreOP_Sseg_image_thr_4 = ants.threshold_image( PreOP_Sseg_image, 4, 4 )

PreOP_ventricles = PreOP_Sseg_image_thr_43 + PreOP_Sseg_image_thr_4
PreOP_ventricles = ants.get_mask(PreOP_ventricles,low_thresh=1,cleanup=0) * 1


PostOP_Sseg_image_thr_43 = ants.threshold_image( PostOP_Sseg_image, 43, 43 )
PostOP_Sseg_image_thr_4 = ants.threshold_image( PostOP_Sseg_image, 4, 4 )

PostOP_ventricles = PostOP_Sseg_image_thr_43 + PostOP_Sseg_image_thr_4
PostOP_ventricles = ants.get_mask(PostOP_ventricles,low_thresh=1,cleanup=0) * 1

PreOP_ventricles.image_write(Get_ventricles+"/PreOP_ventricles.nii.gz",ri=True)
PostOP_ventricles.image_write(Get_ventricles+"/PostOP_ventricles.nii.gz",ri=True)

end = time.time()
recorded_time=end-start
print(recorded_time)
Time_keeping = pd.concat([Time_keeping, pd.DataFrame(['Get_ventricles',recorded_time])], ignore_index=True)

# ========================================
# 5 - Try and manually remove hyperintesity
# So we want to make sure that we have removed hyper intestity and its normally only one or two voxels so lets swap the top 1% with the median
# ========================================

start = time.time()

RemoveHyper=os.path.join(Output_Folder, "S8_RemoveHyper")

if not os.path.exists(RemoveHyper):
    os.makedirs(RemoveHyper)

PreOP_Final_skullstriped_image_for_THR = nib.load(PreOP_Skull_strip_folder+"/Final_skullstriped_image.nii.gz")
PreOP_Final_skullstriped_image_for_THR_fdata = PreOP_Final_skullstriped_image_for_THR.get_fdata()

Pre_99 = np.percentile( PreOP_Final_skullstriped_image_for_THR_fdata[np.nonzero(PreOP_Final_skullstriped_image_for_THR_fdata)] , 99)
Pre_50 = np.percentile(PreOP_Final_skullstriped_image_for_THR_fdata[np.nonzero(PreOP_Final_skullstriped_image_for_THR_fdata)] , 50)

PreOP_Final_skullstriped_image_for_THR_fdata[PreOP_Final_skullstriped_image_for_THR_fdata >= Pre_99] = Pre_50

PRE_save = nib.Nifti1Image(PreOP_Final_skullstriped_image_for_THR_fdata,PreOP_Final_skullstriped_image_for_THR.affine,PreOP_Final_skullstriped_image_for_THR.header)
nib.save(PRE_save,RemoveHyper+"/Pre_Final_skullstriped_image_Manual_remove_hyper.nii.gz")


PostOP_Final_skullstriped_image_for_THR = nib.load(PostOP_Skull_strip_folder+"/Final_skullstriped_image.nii.gz" )
PostOP_Final_skullstriped_image_for_THR_fdata = PostOP_Final_skullstriped_image_for_THR.get_fdata()

Post_99 = np.percentile( PostOP_Final_skullstriped_image_for_THR_fdata[np.nonzero(PostOP_Final_skullstriped_image_for_THR_fdata)] , 99)
Post_50 = np.percentile(PostOP_Final_skullstriped_image_for_THR_fdata[np.nonzero(PostOP_Final_skullstriped_image_for_THR_fdata)] , 50)

PostOP_Final_skullstriped_image_for_THR_fdata[PostOP_Final_skullstriped_image_for_THR_fdata >= Post_99] = Post_50

PostOP_save = nib.Nifti1Image(PostOP_Final_skullstriped_image_for_THR_fdata,PostOP_Final_skullstriped_image_for_THR.affine,PostOP_Final_skullstriped_image_for_THR.header)
nib.save(PostOP_save,RemoveHyper+"/Post_Final_skullstriped_image_Manual_remove_hyper.nii.gz")



end = time.time()
recorded_time=end-start
print(recorded_time)
Time_keeping = pd.concat([Time_keeping, pd.DataFrame(['RemoveHyper',recorded_time])], ignore_index=True)


# ===========================================
# REGISTRATION - LETS TRY EVERYTHING AND PRAY
# ===========================================

# This is for the bash script - these variables will be consistent across all mask creation runs
# "---- Registration - rigid + deformable b-spline syn"

start = time.time()

Do_Registration=os.path.join(Output_Folder, "S9_Registration")

reg_br=os.path.join(Do_Registration, "reg_br")
reg_None_resected=os.path.join(Do_Registration, "reg_None_resected")
reg_None_resected_then_resected=os.path.join(Do_Registration, "reg_None_resected_then_resected")
reg_br_then_resected=os.path.join(Do_Registration, "reg_br_then_resected")

if not os.path.exists(Do_Registration):
    os.makedirs(reg_br)
    os.makedirs(reg_None_resected)
    os.makedirs(reg_None_resected_then_resected)
    os.makedirs(reg_br_then_resected)

PreOP_RemoveHyper = ants.image_read(RemoveHyper+"/Pre_Final_skullstriped_image_Manual_remove_hyper.nii.gz")
PostOP_RemoveHyper = ants.image_read(RemoveHyper+"/Post_Final_skullstriped_image_Manual_remove_hyper.nii.gz" )


antsRegistrationSyN_br = ants.registration(fixed=PreOP_RemoveHyper, moving=PostOP_RemoveHyper, type_of_transform = 'antsRegistrationSyN[br]',outprefix=reg_br+"/br_", n=16)
# antsRegistrationSyN.image_write(Do_Registration+"/PostOP_ventricles.nii.gz",ri=True)

antsRegistrationSyN_br['warpedmovout'].image_write(reg_br+"/warpedmovout.nii.gz",ri=True)
antsRegistrationSyN_br['warpedfixout'].image_write(reg_br+"/warpedfixout.nii.gz",ri=True)

antsRegistrationSyN_br_transformlist = [reg_br+"/br_1Warp.nii.gz" , reg_br+"/br_0GenericAffine.mat"]


end = time.time()
recorded_time=end-start
print(recorded_time)
Time_keeping = pd.concat([Time_keeping, pd.DataFrame(['Regs',recorded_time])], ignore_index=True)



# ===========================================
# TEMP
# ===========================================

# The mask creation step
# for testing see why the code is breaking

RemoveHyper=os.path.join(Output_Folder, "S8_RemoveHyper")
Do_Registration=os.path.join(Output_Folder, "S9_Registration")
reg_br=os.path.join(Do_Registration, "reg_br")
reg_None_resected=os.path.join(Do_Registration, "reg_None_resected")
reg_None_resected_then_resected=os.path.join(Do_Registration, "reg_None_resected_then_resected")
reg_br_then_resected=os.path.join(Do_Registration, "reg_br_then_resected")

PreOP_RemoveHyper = ants.image_read(RemoveHyper+"/Pre_Final_skullstriped_image_Manual_remove_hyper.nii.gz")
PostOP_RemoveHyper = ants.image_read(RemoveHyper+"/Post_Final_skullstriped_image_Manual_remove_hyper.nii.gz" )

Lobe_template_folder=os.path.join(Output_Folder, "S5_Lobe_template")
PreOP_Lobe_template_folder=os.path.join(Lobe_template_folder,'Pre_op')
PostOP_Lobe_template_folder=os.path.join(Lobe_template_folder,'Post_op')

PreOP_Lobe_template_folder_Regions=os.path.join(PreOP_Lobe_template_folder,'Regions')
PreOP_Lobe_template_folder_Lobes=os.path.join(PreOP_Lobe_template_folder,'Lobes')
PreOP_Lobe_template_folder_Dilation=os.path.join(PreOP_Lobe_template_folder,'Dilation')

PostOP_Lobe_template_folder_Regions=os.path.join(PostOP_Lobe_template_folder,'Regions')
PostOP_Lobe_template_folder_Lobes=os.path.join(PostOP_Lobe_template_folder,'Lobes')
PostOP_Lobe_template_folder_Dilation=os.path.join(PostOP_Lobe_template_folder,'Dilation')

Lobe_of_resection=os.path.join(Output_Folder, "S6_Lobe_of_resection")

Get_ventricles=os.path.join(Output_Folder, "S7_Get_ventricles")

Do_Registration=os.path.join(Output_Folder, "S9_Registration")

reg_br=os.path.join(Do_Registration, "reg_br")
reg_None_resected=os.path.join(Do_Registration, "reg_None_resected")
reg_None_resected_then_resected=os.path.join(Do_Registration, "reg_None_resected_then_resected")
reg_br_then_resected=os.path.join(Do_Registration, "reg_br_then_resected")

mri_synthseg_folder=os.path.join(Output_Folder, "S3_mri_synthseg")
PreOP_mri_synthseg_folder=os.path.join(mri_synthseg_folder,'Pre_op')
PostOP_mri_synthseg_folder=os.path.join(mri_synthseg_folder,'Post_op')

PostOP_Sseg_MASK = ants.image_read(PostOP_mri_synthseg_folder+"/PreOP_Sseg_MASK.nii.gz")
PostOP_Sseg_MASK_24 = ants.image_read(PostOP_mri_synthseg_folder+"/PostOP_Sseg_area_24.nii.gz")



POST_the_none_resected_lobe = ants.image_read(Lobe_of_resection+"/PostOP_NONE_feildResection.nii.gz")
PRE_the_none_resected_lobe= ants.image_read(Lobe_of_resection+"/PreOP_NONE_feildResection.nii.gz")
Post_OP_feild_map_Resected_area = ants.image_read(Lobe_of_resection+"/PostOP_feildResection.nii.gz")
Pre_OP_feild_map_Resected_area = ants.image_read(Lobe_of_resection+"/PreOP_feildResection.nii.gz")

PreOP_Sseg_MASK = ants.image_read(PreOP_mri_synthseg_folder+"/PreOP_Sseg_MASK.nii.gz")
PreOP_Sseg_MASK_24 = ants.image_read(PreOP_mri_synthseg_folder+"/PreOP_Sseg_area_24.nii.gz")

PreOP_ventricles = ants.image_read(Get_ventricles+"/PreOP_ventricles.nii.gz")
PostOP_ventricles = ants.image_read(Get_ventricles+"/PostOP_ventricles.nii.gz")

antsRegistrationSyN_br_transformlist = [reg_br+"/br_1Warp.nii.gz" , reg_br+"/br_0GenericAffine.mat"]
antsRegistrationSyN_br_then_resected_transformlist = [reg_br_then_resected+"/reg_br_then_resected_1Warp.nii.gz" , reg_br_then_resected+"/reg_br_then_resected_0GenericAffine.mat"]

antsRegistrationSyN_reg_None_resected_transformlist = [reg_None_resected+"/reg_None_resected_1Warp.nii.gz" , reg_None_resected+"/reg_None_resected_0GenericAffine.mat"]
antsRegistrationSyN_reg_None_resected_then_resected_transformlist = [reg_None_resected_then_resected+"/reg_None_resected_then_resected_1Warp.nii.gz" , reg_None_resected_then_resected+"/reg_None_resected_then_resected_0GenericAffine.mat"]



# ===========================================
# make folders
# ===========================================

start = time.time()

Do_Resection_Mask=os.path.join(Output_Folder, "S10_Make_Resection_Mask")
Do_Resection_Mask_br=os.path.join(Do_Resection_Mask, "reg_br")
Do_Resection_Mask_reg_None_resected=os.path.join(Do_Resection_Mask, "reg_None_resected")
Do_Resection_Mask_reg_None_resected_then_resected=os.path.join(Do_Resection_Mask, "reg_None_resected_then_resected")
Do_Resection_Mask_reg_br_then_resected=os.path.join(Do_Resection_Mask, "reg_br_then_resected")

if not os.path.exists(Do_Resection_Mask):
    os.makedirs(Do_Resection_Mask)
    os.makedirs(Do_Resection_Mask_br)
    os.makedirs(Do_Resection_Mask_reg_None_resected)
    os.makedirs(Do_Resection_Mask_reg_None_resected_then_resected)
    os.makedirs(Do_Resection_Mask_reg_br_then_resected)

The_Resection_Mask=os.path.join(Output_Folder, "S11_The_Resection_Mask")
The_Resection_Mask_br=os.path.join(The_Resection_Mask, "reg_br")
The_Resection_Mask_reg_None_resected=os.path.join(The_Resection_Mask, "reg_None_resected")
The_Resection_Mask_reg_None_resected_then_resected=os.path.join(The_Resection_Mask, "reg_None_resected_then_resected")
The_Resection_Mask_reg_br_then_resected=os.path.join(The_Resection_Mask, "reg_br_then_resected")

if not os.path.exists(The_Resection_Mask):
    os.makedirs(The_Resection_Mask)
    os.makedirs(The_Resection_Mask_br)
    os.makedirs(The_Resection_Mask_reg_None_resected)
    os.makedirs(The_Resection_Mask_reg_None_resected_then_resected)
    os.makedirs(The_Resection_Mask_reg_br_then_resected)


Do_Resection_Mask_v2=os.path.join(Output_Folder, "S10_attempt2")
Do_Resection_Mask_br=os.path.join(Do_Resection_Mask_v2, "reg_br")
if not os.path.exists(Do_Resection_Mask_v2):
    os.makedirs(Do_Resection_Mask_v2)
    os.makedirs(Do_Resection_Mask_br)

# ===========================================
# Resection_Mask br
# ===========================================


## Rescale the images between 0 and 1 - as we want to take one image away from the other so its easy if both images are
Pre_Op_for_rescale = nib.load(RemoveHyper+"/Pre_Final_skullstriped_image_Manual_remove_hyper.nii.gz")
Post_Op_for_rescale = nib.load(reg_br+"/warpedmovout.nii.gz")

Pre_Op_for_rescale_fdata = Pre_Op_for_rescale.get_fdata()
Post_Op_for_rescale_fdata = Post_Op_for_rescale.get_fdata()

Pre_Op_for_rescale_fdata = (Pre_Op_for_rescale_fdata - np.min(Pre_Op_for_rescale_fdata))/np.ptp(Pre_Op_for_rescale_fdata)
Post_Op_for_rescale_fdata = (Post_Op_for_rescale_fdata - np.min(Post_Op_for_rescale_fdata))/np.ptp(Post_Op_for_rescale_fdata)

PRE_save = nib.Nifti1Image(Pre_Op_for_rescale_fdata,Pre_Op_for_rescale.affine,Pre_Op_for_rescale.header)
nib.save(PRE_save,Do_Resection_Mask_br+"/PreOP_rescale.nii.gz")

PostOP_save = nib.Nifti1Image(Post_Op_for_rescale_fdata,Post_Op_for_rescale.affine,Post_Op_for_rescale.header)
nib.save(PostOP_save,Do_Resection_Mask_br+"/PostOP_rescale.nii.gz")

PreOP_rescale = ants.image_read(Do_Resection_Mask_br+"/PreOP_rescale.nii.gz")
PostOP_rescale = ants.image_read(Do_Resection_Mask_br+"/PostOP_rescale.nii.gz")

PreOP_rescale_mask = ants.get_mask(PreOP_rescale,low_thresh=0.000000000000001,cleanup=0)
PostOP_rescale_mask = ants.get_mask(PostOP_rescale,low_thresh=0.000000000000001,cleanup=0)

# Work out the parts of the masks that dont align
difference_in_mask = PreOP_rescale_mask - PostOP_rescale_mask
difference_in_mask = ants.threshold_image( difference_in_mask, 1, 1 )
difference_in_mask.image_write(Do_Resection_Mask_br+"/difference_in_mask.nii.gz",ri=True)

# ===========================================
# Move the post op vents into the pre-op
# ===========================================

POST_the_none_resected_lobe_moving = ants.apply_transforms(fixed=PreOP_RemoveHyper, moving=POST_the_none_resected_lobe, transformlist=antsRegistrationSyN_br_transformlist, interpolator='multiLabel')
POST_the_resected_lobe_moving = ants.apply_transforms(fixed=PreOP_RemoveHyper, moving=Post_OP_feild_map_Resected_area, transformlist=antsRegistrationSyN_br_transformlist, interpolator='multiLabel')

post_op_VENTS_moving = ants.apply_transforms(fixed=PreOP_RemoveHyper, moving=PostOP_ventricles, transformlist=antsRegistrationSyN_br_transformlist, interpolator='multiLabel')
post_op_VENTS_moving_errode = ants.morphology( post_op_VENTS_moving, operation='erode', radius=1, mtype='binary')
post_op_VENTS_moving_Dilate = ants.morphology( post_op_VENTS_moving, operation='dilate', radius=1, mtype='binary')



PostOP_Sseg_MASK_moving = ants.apply_transforms(fixed=PreOP_RemoveHyper, moving=PostOP_Sseg_MASK, transformlist=antsRegistrationSyN_br_transformlist, interpolator='multiLabel')
PostOP_Sseg_MASK_24_moving = ants.apply_transforms(fixed=PreOP_RemoveHyper, moving=PostOP_Sseg_MASK_24, transformlist=antsRegistrationSyN_br_transformlist, interpolator='multiLabel')

PostOP_Sseg_FULL_MASK = PostOP_Sseg_MASK_moving + PostOP_Sseg_MASK_24_moving
PostOP_Sseg_FULL_MASK = ants.get_mask(PostOP_Sseg_FULL_MASK,low_thresh=1,cleanup=0)
PostOP_Sseg_FULL_MASK.image_write(Do_Resection_Mask_br+"/PostOP_Sseg_FULL_MASK.nii.gz",ri=True)

PostOP_Sseg_MASK_moving = ants.morphology( PostOP_Sseg_MASK_moving, operation='erode', radius=1, mtype='binary')
PostOP_Sseg_MASK_moving.image_write(Do_Resection_Mask_br+"/move_PostOP_Sseg_MASK.nii.gz",ri=True)
PostOP_Sseg_MASK_24_moving.image_write(Do_Resection_Mask_br+"/move_PostOP_Sseg_MASK_24.nii.gz",ri=True)

post_op_VENTS_moving.image_write(Do_Resection_Mask_br+"/move_PostOP_vents_to_PreOP.nii.gz",ri=True)
post_op_VENTS_moving_errode.image_write(Do_Resection_Mask_br+"/move_PostOP_vents_to_PreOP_errode.nii.gz",ri=True)


POST_the_none_resected_lobe_moving.image_write(Do_Resection_Mask_br+"/move_POST_the_none_resected_lobe_moving.nii.gz",ri=True)

POST_the_none_resected_lobe_moving = POST_the_none_resected_lobe_moving - post_op_VENTS_moving
post_op_VENTS_moving_errode = post_op_VENTS_moving_errode * 2


Postop_find_csv_priorimage = post_op_VENTS_moving_errode + POST_the_none_resected_lobe_moving
Postop_find_csv_priorimage.image_write(Do_Resection_Mask_br+"/Postop_find_csv_priorimage.nii.gz",ri=True)


Postop_find_csv_atropos = ants.atropos( d=3,a=PostOP_rescale, i ='PriorLabelImage[2,'+Do_Resection_Mask_br+'/Postop_find_csv_priorimage.nii.gz,0]',  m='[0.25]', c='[50,0.01]', x=PostOP_Sseg_MASK_moving)
Post_op_resection_cavity_The_atropos = ants.threshold_image( Postop_find_csv_atropos['segmentation'], 2, 2)

Post_op_resection_cavity_The_atropos = Post_op_resection_cavity_The_atropos * POST_the_resected_lobe_moving
Post_op_resection_cavity_The_atropos = ants.iMath(Post_op_resection_cavity_The_atropos, 'GetLargestComponent')

Post_op_resection_cavity_The_atropos_OVERLAP = Post_op_resection_cavity_The_atropos * post_op_VENTS_moving_Dilate

Post_op_resection_cavity_The_atropos = Post_op_resection_cavity_The_atropos - Post_op_resection_cavity_The_atropos_OVERLAP

Post_op_resection_cavity_The_atropos.image_write(Do_Resection_Mask_br+"/Post_op_resection_cavity.nii.gz",ri=True)


# ===========================================
# Move the post op vents into the pre-op
# ===========================================

Postop_find_csv_atropos_Looking_for_sag = ants.atropos( d=3,a=PostOP_rescale, i ='KMeans[2]',  m='[0.25]', c='[50,0.01]', x=Post_op_resection_cavity_The_atropos)

Postop_find_csv_atropos_Looking_for_sag['segmentation'].image_write(Do_Resection_Mask_br+"/Postop_find_csv_atropos_Looking_for_sag.nii.gz",ri=True)

Postop_find_csv_atropos_Looking_for_sag_ONE = ants.threshold_image( Postop_find_csv_atropos_Looking_for_sag['segmentation'], 1, 1)
Postop_find_csv_atropos_Looking_for_sag_TWO = ants.threshold_image( Postop_find_csv_atropos_Looking_for_sag['segmentation'], 2, 2)

voxels_in_mask_1 = Postop_find_csv_atropos_Looking_for_sag_ONE * PostOP_rescale
voxels_in_mask_2 = Postop_find_csv_atropos_Looking_for_sag_TWO * PostOP_rescale

voxels_in_mask_1.image_write(Do_Resection_Mask_br+"/Postop_find_csv_atropos_Looking_for_sag_IMAGE_one.nii.gz",ri=True)
voxels_in_mask_2.image_write(Do_Resection_Mask_br+"/Postop_find_csv_atropos_Looking_for_sag_IMAGE_two.nii.gz",ri=True)

the_post_op_CSF = ""

voxels_in_mask_1_load = nib.load(Do_Resection_Mask_br+"/Postop_find_csv_atropos_Looking_for_sag_IMAGE_one.nii.gz")
voxels_in_mask_1_load = voxels_in_mask_1_load.get_fdata()

voxels_in_mask_2_load = nib.load(Do_Resection_Mask_br+"/Postop_find_csv_atropos_Looking_for_sag_IMAGE_two.nii.gz")
voxels_in_mask_2_load = voxels_in_mask_2_load.get_fdata()

mask1_median = np.median(voxels_in_mask_1_load[np.nonzero(voxels_in_mask_1_load)])
mask2_median = np.median(voxels_in_mask_2_load[np.nonzero(voxels_in_mask_2_load)])

if mask1_median > mask2_median:

    the_post_op_CSF = ants.get_mask(voxels_in_mask_2,low_thresh=0.000000000000001,cleanup=0)
    the_post_op_CSF = the_post_op_CSF * 2
else:
    the_post_op_CSF = ants.get_mask(voxels_in_mask_1,low_thresh=0.000000000000001,cleanup=0)
    the_post_op_CSF = the_post_op_CSF * 2


# ===========================================
# Resection_Mask br
# ===========================================

## Rescale the images between 0 and 1 - as we want to take one image away from the other so its easy if both images are
Pre_Op_for_rescale = nib.load(RemoveHyper+"/Pre_Final_skullstriped_image_Manual_remove_hyper.nii.gz")
Post_Op_for_rescale = nib.load(reg_br+"/warpedmovout.nii.gz")

Pre_Op_for_rescale_fdata = Pre_Op_for_rescale.get_fdata()
Post_Op_for_rescale_fdata = Post_Op_for_rescale.get_fdata()

Pre_Op_for_rescale_fdata = (Pre_Op_for_rescale_fdata - np.min(Pre_Op_for_rescale_fdata))/np.ptp(Pre_Op_for_rescale_fdata)
Post_Op_for_rescale_fdata = (Post_Op_for_rescale_fdata - np.min(Post_Op_for_rescale_fdata))/np.ptp(Post_Op_for_rescale_fdata)

PRE_save = nib.Nifti1Image(Pre_Op_for_rescale_fdata,Pre_Op_for_rescale.affine,Pre_Op_for_rescale.header)
nib.save(PRE_save,Do_Resection_Mask_br+"/PreOP_rescale.nii.gz")

PostOP_save = nib.Nifti1Image(Post_Op_for_rescale_fdata,Post_Op_for_rescale.affine,Post_Op_for_rescale.header)
nib.save(PostOP_save,Do_Resection_Mask_br+"/PostOP_rescale.nii.gz")

PreOP_rescale = ants.image_read(Do_Resection_Mask_br+"/PreOP_rescale.nii.gz")
PostOP_rescale = ants.image_read(Do_Resection_Mask_br+"/PostOP_rescale.nii.gz")

The_subtracted_image = PostOP_rescale - PreOP_rescale
The_subtracted_image.image_write(Do_Resection_Mask_br+"/The_subtracted_image.nii.gz",ri=True)

PREop_Part_of_the_subtracted = The_subtracted_image * PreOP_Sseg_MASK
PREop_Part_of_the_subtracted.image_write(Do_Resection_Mask_br+"/PREop_Part_of_the_subtracted.nii.gz",ri=True)



post_op_VENTS_moving = ants.apply_transforms(fixed=PreOP_RemoveHyper, moving=PostOP_ventricles, transformlist=antsRegistrationSyN_br_transformlist, interpolator='multiLabel')
post_op_VENTS_moving_errode = ants.morphology( post_op_VENTS_moving, operation='erode', radius=1, mtype='binary')
post_op_VENTS_moving_Dilate = ants.morphology( post_op_VENTS_moving, operation='dilate', radius=1, mtype='binary')
post_op_VENTS_moving.image_write(Do_Resection_Mask_br+"/move_PostOP_vents_to_PreOP.nii.gz",ri=True)

vents_overlap = PreOP_ventricles + post_op_VENTS_moving

vents_overlap = ants.get_mask(vents_overlap,low_thresh=1,cleanup=0)
vents_overlap = ants.morphology( vents_overlap, operation='dilate', radius=1, mtype='binary')
vents_overlap.image_write(Do_Resection_Mask_br+"/vents_overlap.nii.gz",ri=True)


PRE_the_none_resected_lobe_remove_vents = PRE_the_none_resected_lobe - vents_overlap
PRE_the_none_resected_lobe_remove_vents = ants.threshold_image( PRE_the_none_resected_lobe_remove_vents, 1, 1)
PRE_the_none_resected_lobe_remove_vents.image_write(Do_Resection_Mask_br+"/PRE_the_none_resected_lobe_remove_vents.nii.gz",ri=True)


PREop_priorimage = PRE_the_none_resected_lobe_remove_vents + the_post_op_CSF
PREop_priorimage_ONE = ants.threshold_image( PREop_priorimage, 1, 1 )
PREop_priorimage_ONE.image_write(Do_Resection_Mask_br+"/PREop_priorimage_ONE.nii.gz",ri=True)

PREop_priorimage_TWO = ants.threshold_image( PREop_priorimage, 2, 2 )
PREop_priorimage_TWO = PREop_priorimage_TWO * 2
PREop_priorimage_TWO.image_write(Do_Resection_Mask_br+"/PREop_priorimage_TWO.nii.gz",ri=True)

PREop_priorimage = PREop_priorimage_ONE + PREop_priorimage_TWO

PREop_priorimage.image_write(Do_Resection_Mask_br+"/PREop_priorimage.nii.gz",ri=True)

PreOP_Sseg_MASK_errode = ants.morphology( PreOP_Sseg_MASK, operation='erode', radius=1, mtype='binary')

Pre_op_cavity_atropos = ants.atropos( d=3,a=The_subtracted_image, i ='PriorLabelImage[2,'+Do_Resection_Mask_br+'/PREop_priorimage.nii.gz,0]',  m='[0.25]', c='[50,0.01]', x=PreOP_Sseg_MASK_errode)
Pre_op_cavity_atropos['segmentation'].image_write(Do_Resection_Mask_br+"/Pre_op_cavity_atropos.nii.gz",ri=True)



Pre_find_resection_cavity = ants.threshold_image( Pre_op_cavity_atropos['segmentation'], 2, 2)
Pre_find_resection_cavity = Pre_find_resection_cavity * Pre_OP_feild_map_Resected_area
Pre_find_resection_cavity = ants.iMath(Pre_find_resection_cavity, 'GetLargestComponent')
Pre_find_resection_cavity.image_write(Do_Resection_Mask_br+"/Pre_find_resection_cavity.nii.gz",ri=True)

Pre_find_resection_cavity_errode = ants.morphology( Pre_find_resection_cavity, operation='erode', radius=1, mtype='binary')
Pre_find_resection_cavity_errode.image_write(Do_Resection_Mask_br+"/Pre_find_resection_cavity_errode.nii.gz",ri=True)

# get the erroded cavity
The_MAX = nib.load(Do_Resection_Mask_br+"/Pre_find_resection_cavity.nii.gz")
The_MAX_data = The_MAX.get_fdata()


Pre_find_resection_cavity_errode = ants.morphology( Pre_find_resection_cavity, operation='erode', radius=1, mtype='binary')
Pre_find_resection_cavity_errode.image_write(Do_Resection_Mask_br+"/Pre_find_resection_cavity_errode.nii.gz",ri=True)


# get the erroded cavity
The_base_loaded = nib.load(Do_Resection_Mask_br+"/Pre_find_resection_cavity_errode.nii.gz")
The_base_loaded_data = The_base_loaded.get_fdata()
the_expanded_volume = np.count_nonzero(The_base_loaded_data)
pre_base = the_expanded_volume

# Create a blank image that we will add the voxels that we shouldnt expand into
The_no_go_zone = Pre_find_resection_cavity_errode - Pre_find_resection_cavity_errode
The_no_go_zone.image_write(Do_Resection_Mask_br+"/The_no_go_zone.nii.gz",ri=True)

the_difference = 10000

print(the_expanded_volume)

while the_difference > 100:

    The_base_loaded_dilated = nd.binary_dilation(The_base_loaded_data)

    The_base_loaded_dilated = The_base_loaded_dilated * The_MAX_data
    
    The_base_loaded_dilated_save = nib.Nifti1Image(The_base_loaded_dilated,The_base_loaded.affine,The_base_loaded.header)
    nib.save(The_base_loaded_dilated_save,Do_Resection_Mask_br+"/The_base_loaded_dilated_save.nii.gz")
    
    The_no_go_zone_load = nib.load(Do_Resection_Mask_br+"/The_no_go_zone.nii.gz")
    The_no_go_zone_data = The_no_go_zone_load.get_fdata()
    
    
    The_expanded_area = The_base_loaded_dilated - The_base_loaded_data - The_no_go_zone_data
    
    The_expanded_area_save = nib.Nifti1Image(The_expanded_area,The_base_loaded.affine,The_base_loaded.header)
    nib.save(The_expanded_area_save,Do_Resection_Mask_br+"/The_expanded_area_save.nii.gz")
    
    ANTS_The_expanded_area_save = ants.image_read(Do_Resection_Mask_br+"/The_expanded_area_save.nii.gz")
    The_label_clusters=ants.label_clusters(ANTS_The_expanded_area_save,min_cluster_size=0)
    The_label_clusters.image_write(Do_Resection_Mask_br+"/The_label_clusters.nii.gz",ri=True)
        
    
    
    The_label_clusters_loaded = nib.load(Do_Resection_Mask_br+"/The_label_clusters.nii.gz")
    The_label_clusters_loaded_data = The_label_clusters_loaded.get_fdata()
    the_expanded_volume = np.count_nonzero(The_label_clusters_loaded_data)
        
    how_many_clusters = np.max(The_label_clusters_loaded_data)
        
    print(how_many_clusters)

    for x in range(1, int(how_many_clusters) + 1):

        How_large_is_cluster =   np.sum(The_label_clusters_loaded_data == x)
    
        if How_large_is_cluster < 30:
            get_cluster = ants.threshold_image( The_label_clusters, x, x )
            The_no_go_zone = The_no_go_zone + get_cluster
            The_no_go_zone = ants.get_mask(The_no_go_zone,low_thresh=1,cleanup=0)
            The_no_go_zone.image_write(Do_Resection_Mask_br+"/The_no_go_zone.nii.gz",ri=True)

    The_no_go_zone_load = nib.load(Do_Resection_Mask_br+"/The_no_go_zone.nii.gz")
    The_no_go_zone_data = The_no_go_zone_load.get_fdata()

    The_base_loaded_data = The_base_loaded_data + (The_expanded_area - The_no_go_zone_data)
    The_base_loaded_data = np.where(The_base_loaded_data!=0, 1, 0)

    The_base_loaded_data_save = nib.Nifti1Image(The_base_loaded_data,The_base_loaded.affine,The_base_loaded.header)
    nib.save(The_base_loaded_data_save,Do_Resection_Mask_br+"/The_base.nii.gz")

    The_base_stuff = nib.load(Do_Resection_Mask_br+"/The_base.nii.gz")
    The_base_loaded_data = The_base_stuff.get_fdata()
    the_post_expansion = np.count_nonzero(The_base_loaded_data)
  #  print("the post expansion " + str(the_post_expansion))
    
    the_difference = the_post_expansion - pre_base
    pre_base = the_post_expansion
    print('the_difference')
    print(the_difference)

# Get the difference between the border
To_get_distance = nib.load(Do_Resection_Mask_br+"/The_base.nii.gz")
To_get_distance_data = To_get_distance.get_fdata()
To_get_distance_data = 1 - To_get_distance_data
The_distance = nd.distance_transform_edt(To_get_distance_data, return_indices=False)


The_border = nib.load(PreOP_mri_synthseg_folder+"/PreOP_Sseg_area_24.nii.gz")
The_border_data = The_border.get_fdata()

The_border_distance = The_distance * The_border_data

The_border_distance_save = nib.Nifti1Image(The_border_distance,To_get_distance.affine,To_get_distance.header)
nib.save(The_border_distance_save,Do_Resection_Mask_br+"/The_border_distance_save.nii.gz")

Look_at_the_distance_save = nib.Nifti1Image(The_distance,To_get_distance.affine,To_get_distance.header)
nib.save(Look_at_the_distance_save,Do_Resection_Mask_br+"/Look_at_the_distance_save.nii.gz")




# Get the distance from an individual voxel to the border
The_border_data_inv = 1 - The_border_data

The_distance_to_border,indices = nd.distance_transform_edt(The_border_data_inv, return_indices=True)

TO_The_distance_to_border_save = nib.Nifti1Image(The_distance_to_border,The_border.affine,The_border.header)
nib.save(TO_The_distance_to_border_save,Do_Resection_Mask_br+"/TO_The_distance_to_border_save.nii.gz")

The_border_data_BLANK = The_border_data * 0

# For each voxel get the cordinates to it nearest CSF voxel
# Replace the voxel with the CSF voxel distance to the the resection mask voxel (I know confusion)

for x in range(indices.shape[1]):
    for y in range(indices.shape[2]):
        for z in range(indices.shape[3]):

            the_x = indices[0][x][y][z]
            the_y = indices[1][x][y][z]
            the_z = indices[2][x][y][z]

            the_value = The_border_distance[the_x][the_y][the_z]

            Base_voxel_difference = The_distance[x][y][z]

            if the_value > Base_voxel_difference:

                if the_value < 3:
                
                    The_border_data_BLANK[x][y][z] = the_value

                else:
                    The_border_data_BLANK[x][y][z] = 0
                    

            else:

                 The_border_data_BLANK[x][y][z] = 0


# Filter the that image to the area of tissue
PreOP_Sseg_MASK_load = nib.load(PreOP_mri_synthseg_folder+"/PreOP_Sseg_MASK.nii.gz")
PreOP_Sseg_MASK_load_data = PreOP_Sseg_MASK_load.get_fdata()

The_border_data_BLANK = PreOP_Sseg_MASK_load_data * The_border_data_BLANK

The_border_data_BLANK_save = nib.Nifti1Image(The_border_data_BLANK,The_border.affine,The_border.header)
nib.save(The_border_data_BLANK_save,Do_Resection_Mask_br+"/The_voxel_distance_save.nii.gz")


# Get the mask and clean up a little
The_voxel_distance_image = ants.image_read(Do_Resection_Mask_br+"/The_voxel_distance_save.nii.gz")

The_final_mask = ants.get_mask(The_voxel_distance_image,low_thresh=1,cleanup=0)

The_final_mask = ants.iMath(The_final_mask, 'GetLargestComponent')
The_final_mask = ants.morphology(The_final_mask,"close",radius=1)

The_final_mask.image_write(Do_Resection_Mask_br+"/THE_Resection_mask.nii.gz",ri=True)

The_resection_mask_Final=os.path.join(Output_Folder, "RAMPS_Resection_Mask_Output")
if not os.path.exists(The_resection_mask_Final):
    os.makedirs(The_resection_mask_Final)

N4Bias_folder=os.path.join(Output_Folder, "S1_N4bias")
PreOP_N4Bias_folder=os.path.join(N4Bias_folder,'Pre_op')
PostOP_N4Bias_folder=os.path.join(N4Bias_folder,'Post_op')

The_final_mask.image_write(The_resection_mask_Final+"/RAMP_The_resection_mask_in_ORIG.nii.gz",ri=True)

The_final_mask_Pre_resolution=ants.resample_image_to_target(The_final_mask, PreOP_Data_image, interp_type='multiLabel')
The_final_mask_Pre_resolution.image_write(The_resection_mask_Final+"/RAMP_The_resection_mask_in_PRE.nii.gz",ri=True)

PostOP_image = ants.image_read(PostOP_N4Bias_folder+"/Orig_N4bias.nii.gz")

PostOP_op_to_PreOP = ants.apply_transforms(fixed=PreOP_RemoveHyper, moving=PostOP_image, transformlist=antsRegistrationSyN_br_transformlist, interpolator='multiLabel')
PostOP_op_to_PreOP.image_write(The_resection_mask_Final+"/PostOp_Image_in_ORIG.nii.gz",ri=True)
PostOP_op_to_PreOP_Pre_resolution=ants.resample_image_to_target(PostOP_op_to_PreOP, PreOP_Data_image)
PostOP_op_to_PreOP_Pre_resolution.image_write(The_resection_mask_Final+"/PostOp_Image_in_PRE.nii.gz",ri=True)


PreOP_image = ants.image_read(PreOP_N4Bias_folder+"/Orig_N4bias.nii.gz")
PreOP_image.image_write(The_resection_mask_Final+"/PreOp_Image_in_ORIG.nii.gz",ri=True)

PreOP_Data_image.image_write(The_resection_mask_Final+"/PreOp_Image_in_PRE.nii.gz",ri=True)


print(" ========================================== ")
print(" RAMPS completed")
print(" Thank you for using RAMPS ")
print(" ========================================== ")


