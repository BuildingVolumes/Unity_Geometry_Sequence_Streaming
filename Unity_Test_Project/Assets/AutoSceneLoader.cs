using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

public class Scripts : MonoBehaviour
{
    public List<string> sceneNames = new List<string>();

    public float switchintervallSeconds = 10;
    float lastSwitchTimeSeconds = 0;
    int sceneIndex;

    // Start is called before the first frame update
    void Start()
    {
        DontDestroyOnLoad(gameObject);
        lastSwitchTimeSeconds = Time.time;
    }

    // Update is called once per frame
    void Update()
    {
        if(sceneNames.Count > 1)
        {
            if(Time.time - lastSwitchTimeSeconds > switchintervallSeconds)
            {
                lastSwitchTimeSeconds = Time.time;
                sceneIndex++;

                if (sceneIndex >= sceneNames.Count)
                    sceneIndex = 0;

                SceneManager.LoadScene(sceneNames[sceneIndex]);
            }
        }
    }
}
