using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;

public class ShowFPS : MonoBehaviour
{
    TextMeshProUGUI textMesh;
    float avg;

    // Start is called before the first frame update
    void Start()
    {
        textMesh = GetComponent<TextMeshProUGUI>();
    }

    // Update is called once per frame
    void Update()
    {
        avg += ((Time.deltaTime / Time.timeScale) - avg) * 0.03f;
        textMesh.text = Mathf.Round(1f / avg).ToString();
    }
}
