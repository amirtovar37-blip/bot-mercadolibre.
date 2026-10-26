import io
import os
import requests
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image

# -----------------------------------------------------------------------------
# Configuración Inicial de la Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Generador de Publicaciones - Mercado Libre",
    page_icon="🛍️",
    layout="wide"
)

st.title("🛍️ Publicaciones Perfectas para Mercado Libre")
st.markdown(
    "Sube la foto de tu producto para remover el fondo, ajustarlo a **blanco puro (1200x1200px)** "
    "y generar automáticamente el **Título SEO**, la **Ficha Técnica** y la **Descripción** optimizada."
)

# -----------------------------------------------------------------------------
# Barra Lateral: Claves API
# -----------------------------------------------------------------------------
st.sidebar.header("🔑 Configuración de APIs")

env_gemini = os.environ.get("GEMINI_API_KEY", "")
env_removebg = os.environ.get("REMOVE_BG_API_KEY", "")

gemini_key = st.sidebar.text_input("Gemini API Key", value=env_gemini, type="password")
remove_bg_key = st.sidebar.text_input("Remove.bg API Key", value=env_removebg, type="password")

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Requisito Mercado Libre:** La primera imagen debe tener fondo blanco puro (RGB 255,255,255), "
    "sin texto, marcas de agua ni bordes oscuros."
)

# -----------------------------------------------------------------------------
# Funciones Principales
# -----------------------------------------------------------------------------
def procesar_fondo_blanco(input_image_bytes, api_key):
    """
    Recorta el producto usando la API de Remove.bg y lo coloca sobre un lienzo
    blanco puro (RGB 255,255,255) de 1200x1200px.
    """
    response = requests.post(
        'https://api.remove.bg/v1.0/removebg',
        files={'image_file': input_image_bytes},
        data={'size': 'auto'},
        headers={'X-Api-Key': api_key},
    )
    
    if response.status_code == 200:
        img_no_bg = Image.open(io.BytesIO(response.content)).convert("RGBA")
        
        # Crear lienzo blanco puro de 1200x1200 px
        canvas_size = (1200, 1200)
        white_bg = Image.new("RGBA", canvas_size, (255, 255, 255, 255))
        
        # Ajustar tamaño preservando la relación de aspecto
        img_no_bg.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
        
        # Centrar la imagen
        offset = ((canvas_size[0] - img_no_bg.size[0]) // 2, (canvas_size[1] - img_no_bg.size[1]) // 2)
        white_bg.paste(img_no_bg, offset, mask=img_no_bg)
        
        # Convertir a RGB y guardar en buffer JPEG
        output_buffer = io.BytesIO()
        final_img = white_bg.convert("RGB")
        final_img.save(output_buffer, format="JPEG", quality=95)
        return output_buffer.getvalue(), final_img
    else:
        raise Exception(f"Error al procesar fondo en Remove.bg: {response.text}")

def generar_texto_seo(image_bytes, api_key):
    """
    Genera el título SEO (< 60 caracteres), ficha técnica y descripción optimizada
    para Mercado Libre utilizando Gemini 2.5 Flash.
    """
    client = genai.Client(api_key=api_key)
    
    prompt = """
    Eres un especialista elite en e-commerce y SEO para Mercado Libre.
    Analiza minuciosamente la imagen del producto adjunta y genera la publicación perfecta.

    Asegúrate de seguir estrictamente la siguiente estructura:

    ### TÍTULO SEO (MÁXIMO ESTRICTO DE 60 CARACTERES)
    [Sigue la estructura: Producto + Marca + Modelo + Característica clave. No superes nunca los 60 caracteres]

    ### FICHA TÉCNICA Y ATRIBUTOS
    - Marca: [Nombre o Genérica si no se identifica]
    - Modelo: [Modelo identificado o N/A]
    - Condición: Nuevo
    - Características clave: [Puntos destacados extraídos visualmente]

    ### DESCRIPCIÓN OPTIMIZADA
    [Escribe una descripción persuasiva y profesional estructurada en:
    1. Breve introducción atractiva destacando la solución que ofrece el producto.
    2. Lista de beneficios principales y especificaciones técnicas.
    3. Respuestas a dudas frecuentes (compatibilidad, uso, cuidado).
    4. Cierre profesional con llamado a la acción.
    NO incluyas teléfonos, redes sociales, enlaces ni datos de contacto.]
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
            prompt
        ]
    )
    return response.text

# -----------------------------------------------------------------------------
# Carga de Archivos e Interfaz de Usuario
# -----------------------------------------------------------------------------
uploaded_file = st.file_uploader(
    "Selecciona o arrastra la imagen del producto (JPG, PNG, WEBP)",
    type=["jpg", "jpeg", "png", "webp"]
)

if uploaded_file is not None:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📷 Imagen Original")
        st.image(uploaded_file, use_container_width=True)

    btn_procesar = st.button("🚀 Generar Publicación Perfecta", type="primary")

    if btn_procesar:
        if not gemini_key or not remove_bg_key:
            st.error("⚠️ Por favor ingresa ambas claves API (Gemini y Remove.bg) en la barra lateral.")
        else:
            input_bytes = uploaded_file.getvalue()
            
            with st.spinner("1/2 Procesando imagen a Fondo Blanco Puro (1200x1200px)..."):
                try:
                    processed_bytes, final_pil_image = procesar_fondo_blanco(input_bytes, remove_bg_key)
                    
                    with col2:
                        st.subheader("✅ Imagen Optimizada (1200x1200px)")
                        st.image(final_pil_image, use_container_width=True)
                        
                        # Botón para descargar la imagen lista
                        st.download_button(
                            label="📥 Descargar Imagen Fondo Blanco",
                            data=processed_bytes,
                            file_name="mercadolibre_portada.jpg",
                            mime="image/jpeg"
                        )
                except Exception as e:
                    st.error(f"Error procesando la imagen: {e}")
                    st.stop()

            with st.spinner("2/2 Analizando producto y redactando publicación SEO con Gemini..."):
                try:
                    texto_generado = generar_texto_seo(processed_bytes, gemini_key)
                    
                    st.markdown("---")
                    st.subheader("📄 Publicación Generada")
                    st.markdown(texto_generado)
                    
                    # Opción para copiar/descargar el texto generado
                    st.download_button(
                        label="📋 Descargar Texto de la Publicación",
                        data=texto_generado,
                        file_name="publicacion_mercadolibre.txt",
                        mime="text/plain"
                    )
                except Exception as e:
                    st.error(f"Error generando la publicación con Gemini: {e}")
