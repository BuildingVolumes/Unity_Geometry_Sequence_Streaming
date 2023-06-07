---
title: "Preparing your sequences"
description: "How to convert your own sequences into the right format"
lead: "How to convert your own sequences into the right format"
date: 2020-11-16T13:59:39+01:00
lastmod: 2020-11-16T13:59:39+01:00
draft: false
images: []
menu:
  docs:
    parent: "tutorials"
weight: 110
toc: true
---

> 💡If you want to playback data captured with LiveScan3D, you can skip this step, as it's already in the right format 

## Intro

To gurantee high realtime performance, the Geometry Sequence Streamer can only read sequences that are in special file format (.ply for models, .dds for textures). However, to support a
broad spectrum of input formats and make the usage of this plugin as easy as possible, we provide a small converter tool which takes in almost all widely used mesh and image formats, and converts them 
into the correct format for the plugin.
> 👉🏻 Even when your files are already in the .ply/.dds format, they might need to be run through the converter to be encoded correctly!

## Preparation for the conversion
### Naming
In general, you should export your animated mesh or pointcloud sequences from your tool of choice in a way, that each frame of it is saved in a single, independent file. The files should be numbered in some kind of ascending order. This applies to both your models and also textures, if you have any. Save all files into one folder, without subfolders. Example:
```
  frame_1.obj
  frame_2.obj
  frame_3.obj
  ...

  frame_00001.obj
  frame_00002.obj
  frame_00003.obj
  ...

  1_image.png
  2_image.png
  3_image.png
  ...
```

Ensure that the matching images and models for each frame have the same number!

### Supported file formats
The format in which you export your sequence shouldn't matter too much, as a wide variety of the most commonly used formats is supported. 
These are all supported file formats for pointclouds/meshes:

```
.3ds .asc .bre .ctm .dae .e57 .es .fbx .glb .gltf .obj .off .pdb .ply .pts .ptx .qobj .stl .tri vmi .wrl .x3d .xyz
```

And for images:
```
.dds .gif .jpg .png .psd .tga
```


## Converting your sequences

### Installing the converter
1. Download the latest version of the converter tool from here: Download. Currently only windows is supported
2. Unpack the file
3. Open the converter. Go into the unpacked folder and open "GeometrySequenceConverter.exe". Windows might throw a warning that it prevented the app from running, in this case click on "Run anyway" or "More info" and then "Run anyway".

### Using the converter
1. Click on ***Select Input Directory*** ![Converter Select Input](Converter_SelectInput.png)

2. If you don't see any file structure, you may need to click on ***Drives*** ![Converter Select Drive](Converter_SelectDrive.png)

3. Select/Go into the folder which contains your sequence and hit ***Ok*** ![Converter Select Drive](Converter_SelectFolder.png)

4. Now choose your output directory. It has to be a different, empty folder! For convinience, you can click ***Set to Input directory*** to copy the input folder path, and then use ***Select Output Directory*** to choose the empty output folder ![Converter Select Drive](Converter_SelectOutput.png)

5. When you've set your input/output folders, click on ***Start Conversion***. You can optionally choose the amount of threads used for the conversion, which might come in handy for heavy/large sequences. ![Converter Select Drive](Converter_Start_Threads.png)

6. The converter will now process your files and show a progress bar. If you want to cancel the process, click on ***Cancel***. Cancelling might take a bit of time. When the process is done, you'll have the converted sequence inside of the output folder, which you can now move to another location. The files in the output folder will be used to stream the sequence inside of Unity.

## For developers: Format specification
If you want to export your data into the correct format directly, without using the converter, you can do so! The format used here is not proprietory, but uses the open [*Stanford Polygon File Format* (.ply)](http://paulbourke.net/dataformats/ply/ ) for meshes and pointclouds and the [*DirectDraw Surface* (.dds)*](https://en.wikipedia.org/wiki/DirectDraw_Surface) file format for textures/images. However, both formats allow a large variety of encoding, and the Geometry Sequence Streamer needs to be supplemented a special encoding. The following sections assume that you are a bit familiar with both formats. 

### Pointcloud .ply files
For .ply files containing pointclouds, use the normal **little endian binary** .ply standard, but be sure to encode the **vertex positions as 32-bit floats** (not doubles), and use the **vertex colors as uchar RGBA**. You always need to provide the red, green, blue and alpha channel, even when your sequence doesn't use alpha values or colors at all. The alpha channel isn't used in the plugin right now, but it allows for faster file reads, as RGBA is the native Unity vertex color format. Don't include any vertex indices! Here is an example of how the header of a ply looks that is correctly formatted:

```
ply
format binary_little_endian 1.0
comment How the header of a correctly formated .ply file with a pointcloud looks like
element vertex 50000
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
property uchar alpha
end_header
```

As an example for how the data for a a single vertex (line) could look like this. Three XZY-Float values are followed by four RGBA byte/uchar values:
```
0.323434 0.55133 1.44322 255 255 255 0 
```

### Mesh .ply files
For .ply files containing meshes, you use the same **little endian binary** format as for the pointclouds, with the **vertex positions encoded as 32-bit floats**. Encode the **face indices as a uchar uint list**, as it is commonly done in the ply format. Only encode **faces as triangles**, so the uchar component of the face indices list should always be "3", the uInts should be 32-bit.
If you want to use textures/UV-coordinates, include the **U and V-coordinates as additional float propertys (property s and property t)** right behind the xyz properties.
An example header of a correctly formatted mesh ply file with UV-coordinates would look like this:

```
ply
format binary_little_endian 1.0
comment Exported for use in Unity Geometry Streaming Plugin
element vertex 73200
property float x
property float y
property float z
property float s
property float t
element face 138844
property list uchar uint vertex_indices
end_header
```

The data for a single vertex (line) would look like this. Three XYZ-float values, followed by two float values for the UV-coordinates:
```
0.323434 0.55133 1.44322 0.231286 0.692901
```

The data for a single indice (line) in the index list could look like this:
```
3 56542 56543 56544
```

### Textures/Images
The textures should be encoded in the .dds format with **BC1/DXT1** encoding and **no mip-maps**.