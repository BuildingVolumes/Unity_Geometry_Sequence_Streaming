using System.Collections;
using System.Collections.Generic;
using Unity.Mathematics;
using UnityEngine;

public class ComputeShaderPC : MonoBehaviour
{
    public ComputeShader pointcloudShader;
    public Mesh mesh;

    // Start is called before the first frame update
    void Start()
    {

    }

    // Update is called once per frame
    void Update()
    {
        _Point[] pointBufferCPU = new _Point[mesh.vertices.Length];

        for (int i = 0; i < mesh.vertices.Length; i++)
        {
            _Point p = new _Point(mesh.vertices[i], mesh.colors[i]);
            pointBufferCPU[i] = p;
        }

        ComputeBuffer pointBufferGPU = new ComputeBuffer(pointBufferCPU.Length, sizeof(float) * 7);
        pointBufferGPU.SetData(pointBufferCPU);

        pointcloudShader.SetBuffer(0, "_PointBuffer", pointBufferGPU);
    }
}

public struct _Point
{
    public float positionX, positionY, positionZ;
    public float colorR, colorG, colorB, colorA;

    public _Point(Vector3 position, Color color)
    {
        positionX = position.x;
        positionY = position.y;
        positionZ = position.z;

        colorR = color.r;
        colorG = color.g;
        colorB = color.b;
        colorA = color.a;
    }
}
