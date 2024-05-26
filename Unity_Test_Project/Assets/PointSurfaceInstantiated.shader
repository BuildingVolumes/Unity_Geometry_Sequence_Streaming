Shader "GeometryStreaming/PointSurfaceInstantiated"
{
	Properties
	{

	}
	SubShader
	{
		Tags { "RenderType" = "Opaque" }
		LOD 200

		CGPROGRAM
		// Physically based Standard lighting model, and enable shadows on all light types
		#pragma surface surf Standard fullforwardshadows addshadow
		#pragma instancing_options assumeuniformscaling procedural:ConfigureProcedural
		#pragma target 4.5

		struct Input
		{
			float2 uv_MainTex;
		};

		float _Scale;

		#if defined(UNITY_PROCEDURAL_INSTANCING_ENABLED)
		RWByteAddressBuffer _VertexBuffer;
		#endif

		void ConfigureProcedural()
		{

		#if defined(UNITY_PROCEDURAL_INSTANCING_ENABLED)	
		
			//We access the raw vertex buffer of the mesh vertices. As this buffer is raw, we don't have a handy struct to navigate it
			//and need to find the memory addresses ourselves.

			//First, we need to know how much data a vertice contains. Luckily, as we create the mesh ourselves, we know that we have:
			//One Vertex = float3 position, float3 normal, float4 tangent, float2 texCoord0, float 2 texCoord1
			//Which is 14 32bit values, or 14 * 4bytes = 56 bytes per Vertex
			//With this, we can get a memory index
			uint vertexIndex = 1 * 56;
			uint normalIndex = 1 * 56 + 9;

			//All values in the Raw vertex buffer can only be retrieved as ints. So we retrieve our first three ints, which is our position
			uint3 positionRaw = _VertexBuffer.Load3(vertexIndex);
			uint3 normalRaw = _VertexBuffer.Load3(normalIndex);

			//Turn them into floats
			float3 position = asfloat(positionRaw);
			float3 normal = asfloat(positionRaw);

			unity_ObjectToWorld = 0.0;
			unity_ObjectToWorld._m03_m13_m23_m33 = float4(position.x, position.y, position.z, 1.0); //Transformation
			unity_ObjectToWorld._m00_m11_m22 = _Scale;
		#endif
		}

		void surf(Input IN, inout SurfaceOutputStandard o)
		{

			fixed4 c = fixed4(1, 1, 1, 1);
			o.Albedo = c.rgb;
			o.Alpha = c.a;
		}

		ENDCG
	}
		FallBack "Diffuse"
}
