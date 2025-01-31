---
title: "Unity package installation"
description: "Install the Unity package into your project"
lead: "Install the Unity package into your project"
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

## Package Installation

> ⭐ For installation of the Unity Store Version, see section below

1. Open your Unity project, and in the toolbar, go to **Windows --> Package Manager**

2. In the Package Manager window, go into the upper left corner and click on the **"+" Button --> Add package from Git URL** ![Add package with git](package_manager_git.png)

3. Copy and paste the following URL and click **Add**: `https://github.com/BuildingVolumes/Geometry_Sequence_Streaming_Package.git` ![Installing a package](package_manager_add.png)

4. Unity now installs the package, and after a short time it should show up in your manager. Done! We strongly recommend that you also install the [Samples](/docs/tutorials/unity-package-installation/#importing-the-samples)

## Package Installation (Unity Store Version)

1. Open your Unity project, and in the toolbar, go to **Windows --> Package Manager**.

2. In the Package Manager window, go to **My Assets** and select the **Geometry Sequence Streaming Package** ![Select Unity Store Version](package_manager_select_storebought.png)

3. Click on **Install** ![Install Unity Store Version](package_manager_install_storebought.png)

4. Unity now installs the package, and after a short time it should show up in your manager. Done! We strongly recommend that you also install the [Samples](/docs/tutorials/unity-package-installation/#importing-the-samples)

## Importing the samples

The samples contain a short demo sequence and some scenes, that you can refer to for how to set up your own scenes and playback your own sequences.
If you've never used the plugin before, we strongly recommend to take a look at the samples!

To install the samples, **select** the Geometry Streaming Sequence and open the **Sample foldout**. Then click on **import**. ![Add package with git](package_manager_samples.png)

The sample data is now in your Unity assets folder. You can open the sample scenes to take a look how *basic mesh playback*, *basic pointcloud playback*, *timeline playback* and the *scripting API* works. When you open the scene, you should now either see an animated blob mesh, or a winking cat pointcloud!

![Blob](https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExYmVvbXVpazdyanR0dmxyNDhjazNkM3owcnV3NHlwMWFseDRpemoyeiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/XuN1lmgwobrU8eWgsb/giphy.gif)

![Cat](https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdXNtOGozb3d5ZmVwamRjam9zMnBsOXlucXVmemNoanBlN3VlZ2k0YiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/rIT9ggXMG212tkuaIE/giphy.gif)
