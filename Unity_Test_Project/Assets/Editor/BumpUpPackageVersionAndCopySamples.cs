using System.IO;
using UnityEditor;
using UnityEngine;
using Newtonsoft.Json.Linq;
using System;
using BuildingVolumes.Streaming;
using UnityEngine.Playables;
using UnityEngine.Timeline;
using System.Collections.Generic;
using UnityEditor.SceneManagement;
using GluonGui.WorkspaceWindow.Views.WorkspaceExplorer.Explorer;

public class BumpUpPackageVersionAndCopySamples : EditorWindow
{
    string pathToPackage = "C:\\Dev\\Volcapture\\Unity_Geometry_Sequence_Streaming\\Geometry_Sequence_Streaming_Package\\";
    string pathToSamplesRootFolder = "Assets\\Samples\\Geometry Sequence Streaming\\";
    string pathToSamplesFolder = "";
    string pathToNewSamplesFolder = "";

    string pathToPackageJSON = "";
    string pathToSamplesPackageFolder = "";

    string currentVersion = "";
    string packageJSONContent;
    int newMajor;
    int newMinor;
    int newPatch;

    static bool pathValid = false;

    [MenuItem("UGGS Package/Increment package version and copy samples")]
    static void Init()
    {
        BumpUpPackageVersionAndCopySamples window = GetWindow<BumpUpPackageVersionAndCopySamples>();

        window.titleContent = new GUIContent("Change package versioning");
        window.ShowPopup();

        if (!pathValid)
            window.Close();
    }

    private void CreateGUI()
    {
        pathToPackageJSON = Path.Combine(pathToPackage, "package.json");
        pathToSamplesPackageFolder = Path.Combine(pathToPackage, "Samples~\\StreamingSamples\\");

        if (!Directory.Exists(pathToPackage) || !File.Exists(pathToPackageJSON))
        {
            EditorUtility.DisplayDialog("Path invalid!", "Path to package not found! Please change path in script", "Ok");
            pathValid = false;
        }

        else
        {
            GetCurrentPackageVersion();
            pathValid = true;
        }
    }

    void OnGUI()
    {
        GUILayout.Space(20);
        EditorGUILayout.LabelField("Current package version is: " + currentVersion, EditorStyles.wordWrappedLabel);
        GUILayout.Space(20);
        EditorGUILayout.LabelField("Change version to:", EditorStyles.wordWrappedLabel);
        GUILayout.BeginHorizontal();
        newMajor = EditorGUILayout.IntField(newMajor);
        newMinor = EditorGUILayout.IntField(newMinor);
        newPatch = EditorGUILayout.IntField(newPatch);
        GUILayout.EndHorizontal();

        string newVersion = newMajor + "." + newMinor + "." + newPatch;

        pathToSamplesFolder = pathToSamplesRootFolder + currentVersion + "\\Streaming Samples\\";
        pathToNewSamplesFolder = pathToSamplesRootFolder + newVersion + "\\Streaming Samples\\";

        if (GUILayout.Button("Change Version and copy samples"))
        {
            UpdatePackageJSONAndSave(pathToPackageJSON, packageJSONContent, newVersion);
            UpdateSamples(currentVersion, newVersion);
            CopySamples(pathToNewSamplesFolder, pathToSamplesPackageFolder);
            GetCurrentPackageVersion();
            EditorUtility.SetDirty(this);
        }

        if (GUILayout.Button("Just copy samples"))
        {
            CopySamples(pathToNewSamplesFolder, pathToSamplesPackageFolder);
            GetCurrentPackageVersion();
            EditorUtility.SetDirty(this);
        }

    }

    void GetCurrentPackageVersion()
    {
        packageJSONContent = File.ReadAllText(pathToPackageJSON);

        JObject o = JObject.Parse(packageJSONContent);

        JToken version = o.GetValue("version");
        currentVersion = version.Value<string>();
        string[] versionValues = currentVersion.Split('.');
        int major = Int32.Parse(versionValues[0]);
        int minor = Int32.Parse(versionValues[1]);
        int patch = Int32.Parse(versionValues[2]);

        newMajor = major;
        newMinor = minor;
        newPatch = patch;
    }

    void UpdatePackageJSONAndSave(string pathToJson, string jsonContent, string newVersion)
    {
        JObject obj = JObject.Parse(jsonContent);
        obj["version"] = newVersion;

        try
        {
            File.WriteAllText(pathToJson, obj.ToString());
        }

        catch
        {
            Debug.LogError("Could not update package JSON!");
            return;
        }

        Debug.Log("Changed JSON package version to " + newVersion);

    }

    void UpdateSamples(string currentVersion, string newVersion)
    {
        string pathToBasicSceneMesh = pathToSamplesFolder + "01_Basic_Example.unity";
        string pathToBasicScenePC = pathToSamplesFolder + "02_Pointcloud_Example.unity";
        string pathToTimelineScene = pathToSamplesFolder + "03_Timeline_Example.unity";
        string pathToAPIScene = pathToSamplesFolder + "04_API_Example.unity";

        string pathToNewSampleDataMesh = "Samples\\Geometry Sequence Streaming\\" + newVersion + "\\Streaming Samples\\ExampleData\\TexturedMesh_Sequence_Sample";
        string pathToNewSampleDataPC = "Samples\\Geometry Sequence Streaming\\" + newVersion + "\\Streaming Samples\\ExampleData\\Pointcloud_Sequence_Sample";

        UpdateBasicSample(pathToBasicSceneMesh, pathToNewSampleDataMesh);
        UpdateBasicSample(pathToBasicScenePC, pathToNewSampleDataPC);
        UpdateTimelineSample(pathToTimelineScene, pathToNewSampleDataMesh);
        UpdateAPISample(pathToAPIScene, pathToNewSampleDataMesh);
        RenameSamplePath(pathToSamplesRootFolder + currentVersion, pathToSamplesRootFolder + newVersion);
    }

    bool UpdateBasicSample(string pathToScene, string pathToNewSampleData)
    {
        //Basic Sample
        try
        {
            EditorSceneManager.OpenScene(pathToScene, OpenSceneMode.Single);
        }

        catch
        {
            Debug.LogError("Could not load basic sample mesh scene!");
            return false;
        }

        GeometrySequencePlayer player = (GeometrySequencePlayer)FindObjectOfType<GeometrySequencePlayer>();
        if (player.GetRelativeSequencePath() == null)
        {
            Debug.LogError("Could not finde path in basic sample mesh!");
            return false;
        }

        player.SetPath(pathToNewSampleData, GeometrySequenceStream.PathType.RelativeToDataPath);
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        return true;
    }

    bool UpdateTimelineSample(string pathToScene, string pathToNewSampleData)
    {
        //Timeline Sample
        try
        {
            EditorSceneManager.OpenScene(pathToScene, OpenSceneMode.Single);
        }

        catch
        {
            Debug.LogError("Could not load timeline sample scene!");
            return false;
        }


        PlayableDirector director = (PlayableDirector)FindObjectOfType<PlayableDirector>();
        PlayableAsset playable = director.playableAsset;
        TimelineAsset timeline = (TimelineAsset)playable;
        IEnumerable<TimelineClip> clips = timeline.GetRootTrack(1).GetClips();



        foreach (TimelineClip clip in clips)
        {

            GeometrySequenceClip geoClip = (GeometrySequenceClip)clip.asset;

            if (geoClip.relativePath == null)
            {
                Debug.LogError("Could not finde path in timeline Sample!");
                return false;
            }

            geoClip.relativePath = pathToNewSampleData;

        }

        EditorUtility.SetDirty(timeline);
        EditorUtility.SetDirty(playable);
        AssetDatabase.SaveAssets();
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        return true;
    }

    bool UpdateAPISample(string pathToScene, string pathToNewSampleData)
    {
        //API Sample
        try
        {
            EditorSceneManager.OpenScene(pathToScene, OpenSceneMode.Single);
        }

        catch
        {
            Debug.LogError("Could not load API sample scene!");
            return false;
        }

        GeometrySequenceAPIExample api = (GeometrySequenceAPIExample)FindObjectOfType<GeometrySequenceAPIExample>();
        if (api.sequencePath == null)
        {
            Debug.LogError("Could not find path in API Sample!");
            return false;
        }

        api.sequencePath = pathToNewSampleData;
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        return true;
    }

    bool RenameSamplePath(string oldpath, string newpath)
    {
        if (Directory.Exists(oldpath))
        {
            if (oldpath == newpath)
                return true;

            string error = AssetDatabase.MoveAsset(oldpath, newpath);

            if (error != "")
            {
                Debug.LogError("Could not rename sample directory: " + error + " Maybe you need to close Visual Studio?");
                return false;
            }

        }

        else
        {
            Debug.LogError("Sample directory does not exist");
            return false;
        }

        return true;
    }

    void CopySamples(string pathToAssetSamples, string pathToPackageSampleFolder)
    {
        string emptyScene = "Assets\\EmptyScene.unity";
        EditorSceneManager.OpenScene(emptyScene, OpenSceneMode.Single);

        if (!Directory.Exists(pathToAssetSamples) || !Directory.Exists(pathToPackageSampleFolder))
        {
            Debug.LogError("Could not find " + pathToAssetSamples + " or " + pathToPackageSampleFolder);
            return;
        }

        try
        {
            CopyDirectory(pathToAssetSamples, pathToPackageSampleFolder, true);
        }

        catch (Exception e)
        {
            Debug.LogError(e.ToString());
        }
    }

    static void CopyDirectory(string sourceDir, string destinationDir, bool recursive)
    {
        Debug.Log("Copying from: " + sourceDir + " to " + destinationDir);
        // Get information about the source directory
        var dir = new DirectoryInfo(sourceDir);

        // Cache directories before we start copying
        DirectoryInfo[] dirs = dir.GetDirectories();

        //Delete the files in the destination directory
        foreach(string filePath in Directory.GetFiles(destinationDir))
        {
            File.Delete(filePath);
        }



        // Create the destination directory
        Directory.CreateDirectory(destinationDir);


        // Get the files in the source directory and copy to the destination directory
        foreach (FileInfo file in dir.GetFiles())
        {
            string targetFilePath = Path.Combine(destinationDir, file.Name);
            file.CopyTo(targetFilePath, true);
        }

        // If recursive and copying subdirectories, recursively call this method
        if (recursive)
        {
            foreach (DirectoryInfo subDir in dirs)
            {
                string newDestinationDir = Path.Combine(destinationDir, subDir.Name);
                CopyDirectory(subDir.FullName, newDestinationDir, true);
            }
        }
    }
}