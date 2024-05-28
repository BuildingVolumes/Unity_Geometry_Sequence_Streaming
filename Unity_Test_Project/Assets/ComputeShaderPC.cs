using Unity.Mathematics;
using UnityEngine;
using UnityEngine.Rendering;

public class ComputeShaderPC : MonoBehaviour
{
    public ComputeShader pointcloudShader;
    public MeshFilter sourceMeshFilter;
    public MeshFilter outputMeshFilter;
    public Mesh outputMesh;

    public float pointScale = 0.1f;

    //GraphicsBuffer graphicsBuffer;
    //GraphicsBuffer.IndirectDrawIndexedArgs[] graphicsData;

    GraphicsBuffer vertexBuffer;
    GraphicsBuffer indexBuffer;


    static readonly int vertexBufferID = Shader.PropertyToID("_VertexBuffer");
    static readonly int pointSourceID = Shader.PropertyToID("_PointSourceBuffer");
    static readonly int indexBufferID = Shader.PropertyToID("_IndexBuffer");
    static readonly int matrixToSourceWorldID = Shader.PropertyToID("_toSourceWorld");
    static readonly int matrixCameraToWorldID = Shader.PropertyToID("_CameraToWorld");
    static readonly int matrixWorldToCameraID = Shader.PropertyToID("_WorldToCamera");
    static readonly int pointScaleID = Shader.PropertyToID("_PointScale");

    private void Start()
    {
        SetupOutputMesh(sourceMeshFilter.mesh.vertexCount);
    }

    // Update is called once per frame
    void Update()
    {
        // Get the vertex buffer of the source point mesh, and set it up
        // as a buffer parameter to a compute shader. This will act as a
        //position and color source for the rendered points
        sourceMeshFilter.mesh.vertexBufferTarget |= GraphicsBuffer.Target.Raw;
        GraphicsBuffer pointBuffer = sourceMeshFilter.mesh.GetVertexBuffer(0);

        Transform pointRenderTransform = this.transform;
        Transform pointSourceTransform = sourceMeshFilter.GetComponent<Transform>();

        //This point renderer will not always be at the same position as the Point Source object.
        //To handle this, we first convert the coordinates of this point renderer back into local space.
        //From the local space, we then convert them back into the world space of the point source, so that
        //the rendered points are always spatially locked to the point source object.
        Matrix4x4 rendererWorldToLocal = pointRenderTransform.worldToLocalMatrix;     
        Matrix4x4 sourceLocalToWorld = pointSourceTransform.localToWorldMatrix;
        Matrix4x4 toSourceWorld = rendererWorldToLocal * sourceLocalToWorld;

        GraphicsBuffer toSourceWorldBuffer = new GraphicsBuffer(GraphicsBuffer.Target.Structured, 1, 4 * 4 * 4);
        toSourceWorldBuffer.SetData(new Matrix4x4[] {toSourceWorld});

        //We also need to rotate the vertices, so that they always face the camera.
        //For this we get the rotation matrix, that rotates from the source point to the camera
        GraphicsBuffer cameraToWorldBuffer = new GraphicsBuffer(GraphicsBuffer.Target.Structured, 1, 4 * 4 * 4);
        cameraToWorldBuffer.SetData(new Matrix4x4[] { Camera.main.cameraToWorldMatrix });
        GraphicsBuffer worldToCameraBuffer = new GraphicsBuffer(GraphicsBuffer.Target.Structured, 1, 4 * 4 * 4);
        worldToCameraBuffer.SetData(new Matrix4x4[] { Camera.main.worldToCameraMatrix });

        //if (outputMesh != null)
        //    outputMesh.Clear();

        vertexBuffer = outputMesh.GetVertexBuffer(0);
        indexBuffer = outputMesh.GetIndexBuffer();

        pointcloudShader.SetBuffer(0, pointSourceID, pointBuffer);
        pointcloudShader.SetBuffer(0, vertexBufferID, vertexBuffer);
        pointcloudShader.SetBuffer(0, indexBufferID, indexBuffer);
        pointcloudShader.SetBuffer(0, matrixToSourceWorldID, toSourceWorldBuffer);
        pointcloudShader.SetBuffer(0, matrixWorldToCameraID, worldToCameraBuffer);
        pointcloudShader.SetBuffer(0, matrixCameraToWorldID, cameraToWorldBuffer);  
        pointcloudShader.SetFloat(pointScaleID, pointScale);  
        pointcloudShader.Dispatch(0, Mathf.CeilToInt(sourceMeshFilter.sharedMesh.vertexCount / 128f), 1, 1);

        outputMeshFilter.sharedMesh = outputMesh;

        pointBuffer.Release();
        vertexBuffer.Release();
        indexBuffer.Release();
        toSourceWorldBuffer.Release();
        worldToCameraBuffer.Release();
        cameraToWorldBuffer.Release();
    }

    void SetupOutputMesh(int pointCount)
    {
        outputMesh = new Mesh();

        outputMesh.indexBufferTarget |= GraphicsBuffer.Target.Raw;
        outputMesh.vertexBufferTarget |= GraphicsBuffer.Target.Raw;

        VertexAttributeDescriptor vp = new VertexAttributeDescriptor(VertexAttribute.Position, VertexAttributeFormat.Float32, 3);

        outputMesh.SetVertexBufferParams(pointCount * 4, vp);
        outputMesh.SetIndexBufferParams(pointCount * 6, IndexFormat.UInt32);

        outputMesh.SetSubMesh(0, new SubMeshDescriptor(0, pointCount * 6), MeshUpdateFlags.DontRecalculateBounds);

        vertexBuffer = outputMesh.GetVertexBuffer(0);
        indexBuffer = outputMesh.GetIndexBuffer();

    }
}

