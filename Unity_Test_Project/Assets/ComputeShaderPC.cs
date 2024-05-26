using System.Collections;
using System.Collections.Generic;
using Unity.Mathematics;
using UnityEngine;
using UnityEngine.Rendering;

public class ComputeShaderPC : MonoBehaviour
{
    public ComputeShader pointcloudShader;
    public MeshFilter sourceMesh;
    public Mesh outputMesh;

    //GraphicsBuffer graphicsBuffer;
    //GraphicsBuffer.IndirectDrawIndexedArgs[] graphicsData;

    GraphicsBuffer vertexBuffer;
    GraphicsBuffer indexBuffer;

    static readonly int scaleID = Shader.PropertyToID("_Scale");
    static readonly int vertexBufferID = Shader.PropertyToID("_VertexBuffer");

    // Start is called before the first frame update
    void Start()
    {
        //graphicsBuffer = new GraphicsBuffer(GraphicsBuffer.Target.IndirectArguments, 1, GraphicsBuffer.IndirectDrawIndexedArgs.size);
        //graphicsData = new GraphicsBuffer.IndirectDrawIndexedArgs[1];
    }

    // Update is called once per frame
    void Update()
    {

        sourceMesh.mesh.vertexBufferTarget |= GraphicsBuffer.Target.Raw;
        // Get the vertex buffer of the Mesh, and set it up
        // as a buffer parameter to a compute shader.
        GraphicsBuffer pointBuffer = sourceMesh.mesh.GetVertexBuffer(0);


        Matrix4x4 localToWorld = sourceMesh.GetComponent<Transform>().localToWorldMatrix;
        GraphicsBuffer localToWorldBuf = new GraphicsBuffer(GraphicsBuffer.Target.Structured, 1, 4 * 4 * 4);
        localToWorldBuf.SetData(new Matrix4x4[] {localToWorld});

        //float[] original = new float[14 * sourceMesh.sharedMesh.vertexCount];

        //float[] vertices = new float[14 * sourceMesh.sharedMesh.vertexCount];

        //vertexBuffer.GetData(original);

        SetupOutputMesh(sourceMesh.mesh.vertexCount);

        pointcloudShader.SetBuffer(0, "_PointBuffer", pointBuffer);
        pointcloudShader.SetBuffer(0, "_VertexBuffer", vertexBuffer);
        pointcloudShader.SetBuffer(0, "_IndexBuffer", indexBuffer);
        pointcloudShader.SetBuffer(0, "_LocalToWorldMatrix", localToWorldBuf);
        pointcloudShader.Dispatch(0, Mathf.CeilToInt(sourceMesh.sharedMesh.vertexCount / 128f), 1, 1);

        GetComponent<MeshFilter>().mesh = outputMesh;

        //vertexBuffer.GetData(vertices);

        //Mesh shared = sourceMesh.mesh;

        //for (int i = 0; i < shared.vertexCount; i++)
        //{
        //    shared.vertices[i].Set(vertices[i * 14 + 0], vertices[i * 14 + 1], vertices[i * 14 + 2]);
        //}


        //RenderParams rp = new RenderParams(instancedMat);
        //rp.worldBounds = new Bounds(Vector3.zero, Vector3.one * 100);
        //rp.matProps = new MaterialPropertyBlock();
        //rp.matProps.SetBuffer("_VertexBuffer", vertexBuffer);
        //rp.matProps.SetFloat(scaleID, 0.2f);
        //graphicsData[0].indexCountPerInstance = instancedMesh.GetIndexCount(0);
        //graphicsData[0].instanceCount = (uint)sourceMesh.mesh.vertexCount;
        //graphicsBuffer.SetData(graphicsData);

        //Graphics.RenderMeshIndirect(rp, instancedMesh, graphicsBuffer);
    }

    void SetupOutputMesh(int pointCount)
    {
        outputMesh = new Mesh();

        outputMesh.indexBufferTarget |= GraphicsBuffer.Target.Raw;
        outputMesh.vertexBufferTarget |= GraphicsBuffer.Target.Raw;

        VertexAttributeDescriptor vp = new VertexAttributeDescriptor(VertexAttribute.Position, VertexAttributeFormat.Float32, 3);
        VertexAttributeDescriptor vn = new VertexAttributeDescriptor(VertexAttribute.Normal, VertexAttributeFormat.Float32, 3);

        outputMesh.SetVertexBufferParams(pointCount * 4, vp, vn);
        outputMesh.SetIndexBufferParams(pointCount * 6, IndexFormat.UInt32);

        outputMesh.SetSubMesh(0, new SubMeshDescriptor(0, pointCount * 6), MeshUpdateFlags.DontRecalculateBounds);

        vertexBuffer = outputMesh.GetVertexBuffer(0);
        indexBuffer = outputMesh.GetIndexBuffer();

    }
}

