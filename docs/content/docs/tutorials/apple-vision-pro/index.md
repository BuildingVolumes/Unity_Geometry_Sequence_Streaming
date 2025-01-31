---
title: "Apple Vision Pro"
description: "Special considerations for the Apple Vision Pro platform"
lead: "Apple Vision Pro "
date: 2020-11-16T13:59:39+01:00
lastmod: 2020-11-16T13:59:39+01:00
draft: false
images: []
menu:
  docs:
    parent: "tutorials"
weight: 170
toc: true
---

> ⭐ Building for the Apple Vision Pro is only supported in the Unity Asset Store version

## Considerations when building for the Apple Vision Pro

Unity Apps can run in three distinct modes on the Apple Vision Pro: A **flat 2D mode**, where apps appear on a virtual screen, the **bounded mode**, and the **immersive mode**.
All modes are supported by this plugin. While the **flat mode** runs like an IPhone or IPad application, there are stark differences between the **bounded** and **immersive** mode.
We generally recommended to use the **immersive** mode whenever you can, due to it's much higher performance capabilities.

### Bounded mode

The bounded mode lets the users run an app along other apps, inside a limited volume, comparable to a 3D window. Apps running in this mode face many restrictions, including not being able to render their content natively. Unity needs to translate all meshes, textures, materials and shaders to RealityKit equivalents, this is called the **PolySpatial** pipeline. Due to these restrictions, playback performance suffers and works only for smaller sequences. Pointclouds sequences should stay under **50.000 points per frame**, mesh sequences under **30.000 polygons per frame**, and textures at or under **2048x2048 texture resolution** per frame. Additionally, there might be a performance ditch when the sequence starts, especially for pointcloud sequences. These are gradually streamed in to not overload the system.

Bounded mode is usually detected automatically. For this to work, you need to have a volume camera component inside your scene.

### Immersive mode

Immersive mode lets the application take over the full rendering on the Apple Vision Pro, which is much more comparable to how apps are run on other headsets, such as the Meta Quest. While no other content than the application can exist in the same space, this mode **increases performance** by a huge margin compared to the bounded mode. We were able to run sequences with 1.5 millions points per frame and more! Please ensure that **no volume camera exists** in your scene if you use this mode, otherwise the bounded rendering path might get erroneously activated by the Geometry Sequence Streaming package.
