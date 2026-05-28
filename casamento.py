import streamlit as st
import pandas as pd
import json
import urllib.parse
import os
import io
import binascii
from datetime import datetime
from supabase import create_client, Client, ClientOptions
import qrcode

# -------------------------------
# Configurações básicas
# -------------------------------
NOME_DOS_NOIVOS = "Ana Paula & Talles"
DATA_DO_CASAMENTO = "15 de Agosto de 2026, 16:00"
MENSAGEM_BOAS_VINDAS = """Sejam bem vindos ao nosso site!

Estamos muito felizes em ter vocês aqui. Criamos este cantinho com carinho para compartilhar um pouco da nossa história e reunir todas as informações do nosso grande dia.

Esperamos que este site ajude vocês a se preparar para celebrar, rir, dançar e viver esse momento especial com a gente.
A presença de vocês já torna tudo ainda mais bonito, mal podemos esperar por esse dia!

Com carinho,

Ana Paula e Talles"""


# Dados do recebedor (exatamente como cadastrados na chave Pix)
#CHAVE_PIX = "9a006f14-6348-4996-97a2-9934e1578604"
#NOME_RECEBEDOR = "Talles Silva Rodrigues"
#CIDADE_RECEBEDOR = "SAO PAULO"
#TXID_PIX = "2kNBVR4rOd"   # txid alfanumérico (não use ***)

NOME_RECEBEDOR = "ANA P C PROCOPIO"
CIDADE_RECEBEDOR = "RIBEIRAO PRET"
CHAVE_PIX = "anaetalles.15.08@hotmail.com"
TXID_PIX = "***"

MENSAGEM_PIX = "Se preferir presente em Pix, use a chave acima. Obrigado pelo carinho!"
ENDERECO_CERIMONIA = "Paróquia São Cristovão, R. Padre Américo Ceppi, 190, Centro, Uberlândia"
HORARIO_CERIMONIA = "16:00"
ENDERECO_FESTA = "Espaço Parnassus, R. do Prata, 1703 - Chacaras Bonanza"
HORARIO_FESTA = "19:00"



st.set_page_config(
    page_title="Ana Paula & Talles",
    page_icon="\U0001f48d",
    layout="centered",
)


# -------------------------------
# Funções Supabase 
# -------------------------------
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    if os.getenv("STREAMLIT_ENV") != "cloud":
        import httpx
        options = ClientOptions(httpx_client=httpx.Client(verify=False))
        return create_client(url, key, options)
    return create_client(url, key)

supabase = get_supabase()

def salvar_rsvp(row: dict):
    supabase.table("rsvp").insert(row).execute()

def carregar_rsvp() -> pd.DataFrame:
    res = supabase.table("rsvp").select("*").order("timestamp", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(
        columns=["timestamp", "nome", "email", "telefone", "presenca", "qtd_pessoas", "mensagem", "acompanhantes"]
    )

def salvar_gift(row: dict):
    supabase.table("gifts").insert(row).execute()

def carregar_gifts() -> pd.DataFrame:
    res = supabase.table("gifts").select("*").order("timestamp", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(
        columns=["timestamp", "nome", "presente", "link", "mensagem"]
    )

def salvar_foto(nome_autor: str, filename: str, dados: bytes, content_type: str = "image/jpeg"):
    bucket = "photos"
    path = f"{datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')}-{filename}"
    supabase.storage.from_(bucket).upload(path, dados, {"content-type": content_type})
    supabase_url = st.secrets["supabase"]["url"].rstrip("/")
    url = f"{supabase_url}/storage/v1/object/public/{bucket}/{path}"
    supabase.table("photos").insert({
        "timestamp": datetime.utcnow().isoformat(),
        "autor": nome_autor,
        "url": url,
        "filename": path,
    }).execute()
    return url

def carregar_fotos() -> pd.DataFrame:
    res = supabase.table("photos").select("*").order("timestamp", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(
        columns=["timestamp", "autor", "url", "filename"]
    )

# -------------------------------
# Funções utilitárias
# -------------------------------
def slugify(text: str) -> str:
    t = "".join(ch if ch.isalnum() else "-" for ch in text.lower())
    t = "-".join(filter(None, t.split("-")))
    return t[:60]

def human_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return ts

def parse_preco(preco_str: str) -> float:
    try:
        v = preco_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
        return float(v)
    except Exception:
        return 0.0


# -------------------------------
# Geração do Pix BR Code (EMV)
# usando CRC16 NATIVO do Python (binascii.crc_hqx)
# -------------------------------
def _format_field(field_id: str, value: str) -> str:
    return f"{field_id}{len(value):02d}{value}"

def _crc16_pix(payload: str) -> str:
    """CRC16-CCITT-FALSE (poly 0x1021, init 0xFFFF) — nativo do Python."""
    crc = binascii.crc_hqx(payload.encode("utf-8"), 0xFFFF)
    return f"{crc:04X}"
def gerar_payload_pix(chave: str, nome_recebedor: str, cidade: str, txid: str = "***") -> str:
    """Gera o Pix Copia e Cola (BR Code estático) no padrão EMV do Banco Central."""
    nome_recebedor = nome_recebedor[:25]
    cidade = cidade[:15]
    
    # # 00 - Payload Format Indicator Talles
    # payload  = _format_field("00", "01")
    # # 26 - Merchant Account Info (Pix) — note BR.GOV.BCB.PIX em MAIÚSCULO
    # mai      = _format_field("00", "BR.GOV.BCB.PIX") + _format_field("01", chave)
    # payload += _format_field("26", mai)
    # # 52 - MCC
    # payload += _format_field("52", "0000")
    # # 53 - Moeda BRL
    # payload += _format_field("53", "986")
    # # 58 - País
    # payload += _format_field("58", "BR")
    # # 59 - Nome
    # payload += _format_field("59", nome_recebedor)
    # # 60 - Cidade
    # payload += _format_field("60", cidade)
    # # 62 - Additional Data (txid)
    # payload += _format_field("62", _format_field("05", txid))
    # # 63 - CRC16 (usando binascii.crc_hqx nativo)
    # payload += "6304"

    # 00 - Payload Format Indicator Ana
    payload  = _format_field("00", "01")                  # Payload Format Indicator
    payload += _format_field("01", "11")                  # Point of Initiation = 11
    
    mai      = _format_field("00", "br.gov.bcb.pix") + _format_field("01", chave)
    payload += _format_field("26", mai)                   # Merchant Account Info (Pix)
    
    payload += _format_field("52", "0000")                # MCC
    payload += _format_field("53", "986")                 # Moeda BRL
    
    # ---> AQUI ENTRA O VALOR NO PAYLOAD (Campo 54) <---
    if valor > 0:
        payload += _format_field("54", f"{valor:.2f}")
        
    payload += _format_field("58", "BR")                  # País
    payload += _format_field("59", nome_recebedor)        # Nome
    payload += _format_field("60", cidade)                # Cidade
    payload += _format_field("62", _format_field("05", "***"))  # txid
    payload += "6304"                                     # CRC field header
    
    payload += _crc16_pix(payload)
    return payload

@st.cache_data
def gerar_qrcode_pix(chave: str, valor: float) -> tuple:
    """Retorna (PNG bytes, payload copia-e-cola)."""
    # Passando o valor para a geração do payload
    payload = gerar_payload_pix(chave, NOME_RECEBEDOR, CIDADE_RECEBEDOR, valor)
    
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read(), payload


# -------------------------------
# Estilos
# -------------------------------
st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(rgba(255,250,188,0.15), rgba(255,250,188,0.05)),
                        url('https://zamgppdvwnzgptoftgta.supabase.co/storage/v1/object/public/photos/Frame%202%20(1).png')
                        no-repeat center center fixed;
            background-size: cover;
        }
        [data-testid="stSidebar"] {
            background-color: rgba(30,30,30,0.3);
            backdrop-filter: blur(3px);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500&family=Dancing+Script:wght@600&display=swap');
h1 { color:#050505; font-family:'Dancing Script', cursive !important; font-size:2rem !important; }
h2, h3 { color:#050505; }
h2 { font-size:2rem !important; } h3 { font-size:1rem !important; }
p, li, label { color:#050505; font-size:1rem !important; }
span { color:#050505; font-size:3rem !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    div[data-testid="stForm"] div.stFormSubmitButton > button,
    button[data-testid="stBaseButton-secondary"],
    button[data-testid="stBaseLinkButton-secondary"] {
        background-color: #daa520 !important;
        color: #050505 !important;
        border: none !important;
        border-radius: 8px;
        padding: 10px 20px;
    }
    div[data-testid="stFileUploaderDropzoneInstructions"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------
# Cabeçalho
# -------------------------------
st.title(f"{NOME_DOS_NOIVOS}")

# -------------------------------
# Sidebar
# -------------------------------
st.sidebar.title("Menu")
pagina = st.sidebar.radio(
    "",
    (
        " Pagina Principal",
        " Confirmação de Presença",
        " Lista de Presentes",
        " Endereço dos Eventos",
        " Galeria de Fotos",
    ),
    index=0,
)

with st.sidebar:
    st.markdown("---")
    st.subheader("Música ambiente")
    st.components.v1.html("""
    <iframe id="sc-player" width="250" height="150" scrolling="no" frameborder="no" allow="autoplay"
      src="https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/150679477&color=%23ff5500&auto_play=false&hide_related=false&show_comments=false&show_user=true&show_reposts=false&show_teaser=false&visual=false">
    </iframe>
    <script src="https://w.soundcloud.com/player/api.js"></script>
    <div style="display:flex; gap:8px; align-items:center; margin-top:6px;">
      <button id="unmute" style="padding:6px 10px; font-size:14px;">Ativar som 🎵</button>
      <span id="status" style="font-size:12px; color:#555;">Clique para ativar</span>
    </div>
    <script>
      const widget = SC.Widget(document.getElementById('sc-player'));
      const status = document.getElementById('status');
      const unmuteBtn = document.getElementById('unmute');
      widget.bind(SC.Widget.Events.READY, function() {
        widget.setVolume(0);
        status.textContent = 'Clique em "Ativar som"';
      });
      unmuteBtn.addEventListener('click', function() {
        widget.setVolume(80);
        widget.play();
        status.textContent = 'Tocando';
      });
    </script>
    """, height=260)

# ================================
# Home
# ================================
if pagina == " Pagina Principal":
    with open("Entrada.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    st.components.v1.html(html_content, height=340)
    st.write(MENSAGEM_BOAS_VINDAS)

# ================================
# Confirmação de Presença
# ================================
elif pagina == " Confirmação de Presença":
    st.subheader(" Confirmação de Presença")
    st.write("Por favor, preencha suas informações para confirmar ou justificar sua ausência.")

    if "acomp_count" not in st.session_state:
        st.session_state.acomp_count = 0
    if "rsvp_msg" not in st.session_state:
        st.session_state.rsvp_msg = None

    if st.session_state.rsvp_msg:
        st.success(st.session_state.rsvp_msg)
        st.session_state.rsvp_msg = None

    with st.form("rsvp_form", clear_on_submit=True, enter_to_submit=False):
        nome     = st.text_input("Nome completo*",  placeholder="Seu nome")
        email    = st.text_input("E-mail",           placeholder="seu@email.com")
        telefone = st.text_input("Telefone",         placeholder="(xx) xxxxx-xxxx")
        presença = st.radio("Você vai ao casamento?",
            ["Sim, confirmo presença", "Infelizmente não poderei ir"])
        msg = st.text_area("Mensagem aos noivos (opcional)", placeholder="Deixe um recado carinhoso")

        acompanhantes = []
        if st.session_state.acomp_count > 0:
            st.markdown("**Dados dos acompanhantes**")
        for i in range(st.session_state.acomp_count):
            c1, c2 = st.columns([3, 2])
            ac_nome = c1.text_input(f"Nome do acompanhante {i+1}", key=f"acomp_nome_{i}")
            ac_obs  = c2.text_input(f"Obs./Parentesco {i+1} (opcional)", key=f"acomp_obs_{i}")
            acompanhantes.append({"nome": ac_nome.strip(), "obs": ac_obs.strip()})

        enviar = st.form_submit_button("Enviar confirmação", type="primary")

    st.subheader("Acompanhantes")
    col_add, col_remove = st.columns(2)
    add_clicked    = col_add.button("Adicionar acompanhante +", type="primary")
    remove_clicked = col_remove.button("Remover último -", type="primary")
    if add_clicked:
        st.session_state.acomp_count += 1
        st.rerun()
    if remove_clicked and st.session_state.acomp_count > 0:
        st.session_state.acomp_count -= 1
        st.rerun()
    if st.session_state.acomp_count > 0:
        st.caption(f"Acompanhantes adicionados: {st.session_state.acomp_count}")

    if enviar:
        if not nome.strip():
            st.error("Por favor, informe seu nome.")
        else:
            acompanhantes_validos = [a for a in acompanhantes if a["nome"]]
            qtd_pessoas = 1 + len(acompanhantes_validos)
            row = {
                "timestamp":     datetime.utcnow().isoformat(),
                "nome":          nome.strip(),
                "email":         email.strip(),
                "telefone":      telefone.strip(),
                "presenca":      "Sim" if presença.startswith("Sim") else "Não",
                "qtd_pessoas":   qtd_pessoas,
                "mensagem":      msg.strip(),
                "acompanhantes": json.dumps(acompanhantes_validos, ensure_ascii=False),
            }
            try:
                salvar_rsvp(row)
                if len(acompanhantes_validos) == 0:
                    st.session_state.rsvp_msg = (
                        f"✅ Confirmação registrada!\n\n"
                        f"👤 Titular: **{nome.strip()}**\n\n"
                        f"🎉 Total confirmado: **1 pessoa**"
                    )
                else:
                    nomes_acomp = ", ".join([a["nome"] for a in acompanhantes_validos])
                    st.session_state.rsvp_msg = (
                        f"✅ Confirmação registrada com sucesso!\n\n"
                        f"👤 Titular: **{nome.strip()}**\n\n"
                        f"👥 Acompanhantes ({len(acompanhantes_validos)}): {nomes_acomp}\n\n"
                        f"🎉 Total de pessoas confirmadas: **{qtd_pessoas}**"
                    )
                for i in range(st.session_state.acomp_count):
                    st.session_state.pop(f"acomp_nome_{i}", None)
                    st.session_state.pop(f"acomp_obs_{i}", None)
                st.session_state.acomp_count = 0
                st.rerun()
            except Exception as e:
                st.error(f"Não foi possível salvar sua confirmação. Erro: {e}")

# ================================
# Lista de Presentes
# ================================
elif pagina == " Lista de Presentes":
    st.header("Lista de Presentes e Pix")
    st.write("Fique à vontade para escolher um presente. Se preferir, pode usar nossa chave Pix.")

    st.subheader("Pix")
    st.write(f"Chave Pix: {CHAVE_PIX}")
    st.write(MENSAGEM_PIX)

    st.divider()

    st.subheader("Sugestões de Presentes")
    st.caption("Clique em um presente para ver o QR Code Pix pronto para pagar.")

    presentes = [
        {"nome": "Caixa de emergências para dias difíceis (doces inclusos)", "preco": "R$ 85", "emoji": "🍫",
         "img": "https://images.unsplash.com/photo-1548907040-4baa42d10919?w=600&h=400&fit=crop"},
        {"nome": "Patrocínio de cafés da manhã preguiçosos de domingo", "preco": "R$ 90", "emoji": "🥞",
         "img": "https://images.unsplash.com/photo-1533089860892-a7c6f0a88666?w=600&h=400&fit=crop"},
        {"nome": "Ajuda para renovar o estoque de vinho da casa", "preco": "R$ 100", "emoji": "🍷",
         "img": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?w=600&h=400&fit=crop"},
        {"nome": "Fundo para petiscos em noites com amigos", "preco": "R$ 70", "emoji": "🍕",
         "img": "https://images.unsplash.com/photo-1528605248644-14dd04022da1?w=600&h=400&fit=crop"},
        {"nome": "Kit ração e sachê para os pets da casa", "preco": "R$ 65", "emoji": "🐾",
         "img": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=600&h=400&fit=crop"},
        {"nome": "Vale-plantinha para deixar o nosso lar ainda mais bonito", "preco": "R$ 80", "emoji": "🪴",
         "img": "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=600&h=400&fit=crop"},
        {"nome": "Ajuda para comprar livros e itens colecionáveis de Senhor dos Anéis para o noivo", "preco": "R$ 180", "emoji": "🧝‍♂️",
         "img": "https://images.unsplash.com/photo-1506880018603-83d5b814b5a6?w=600&h=400&fit=crop"},
        {"nome": "Fundo para jantares especiais a dois", "preco": "R$ 250", "emoji": "🍝",
         "img": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&h=400&fit=crop"},
        {"nome": "Contribuição para nossa primeira viagem de casados", "preco": "R$ 300", "emoji": "✈️",
         "img": "https://images.unsplash.com/photo-1488085061387-422e29b40080?w=600&h=400&fit=crop"},
        {"nome": "Vale-paciência para ouvir a noiva falar do casamento pela 472ª vez", "preco": "R$ 150", "emoji": "👰‍♀️",
         "img": "https://images.unsplash.com/photo-1519741497674-611481863552?w=600&h=400&fit=crop"},
        {"nome": "Ajuda para seguirmos firmes da vida fitness", "preco": "R$ 220", "emoji": "🏋️",
         "img": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=600&h=400&fit=crop"},
        {"nome": "Fundo para construção de um laboratório para a noiva fazer experiências", "preco": "R$ 200", "emoji": "🔬",
         "img": "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=600&h=400&fit=crop"},
        {"nome": "Vale-date romântico surpresa", "preco": "R$ 290", "emoji": "🌹",
         "img": "https://images.unsplash.com/photo-1529543544282-ea669407fca3?w=600&h=400&fit=crop"},
        {"nome": "Vale-paciência para ouvir o noivo contar curiosidades sobre o Michael Jackson pela 586ª vez", "preco": "R$ 110", "emoji": "🕺",
         "img": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=600&h=400&fit=crop"},
        {"nome": "Fundo oficial para sustentar o plano do noivo de ser um corredor", "preco": "R$ 140", "emoji": "🏃‍♂️",
         "img": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600&h=400&fit=crop"},
        {"nome": "Vale automobilístico para aprimorar a moto do noivo", "preco": "R$ 170", "emoji": "🏍️",
         "img": "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=600&h=400&fit=crop"},
        {"nome": "Contribuição para os noivos viajarem de moto pelo país", "preco": "R$ 160", "emoji": "🛣️",
         "img": "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=600&h=400&fit=crop"},
        {"nome": "Fundo para custear as \"comprinhas\" da shopee da noiva", "preco": "R$ 500", "emoji": "🛍️",
         "img": "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=600&h=400&fit=crop"},
        {"nome": "Vale-jantar romântico na lua de mel", "preco": "R$ 350", "emoji": "🥂",
         "img": "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=600&h=400&fit=crop"},
        {"nome": "Ajuda para o noivo montar o setup de trabalho", "preco": "R$ 450", "emoji": "💻",
         "img": "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=600&h=400&fit=crop"},
        {"nome": "Patrocínio oficial das nossas pequenas aventuras", "preco": "R$ 400", "emoji": "🏕️",
         "img": "https://images.unsplash.com/photo-1504280658369-0820e129f10a?w=600&h=400&fit=crop"},
        {"nome": "Fundo para compra da chácara no meio do mato que o noivo sonha", "preco": "R$ 320", "emoji": "🏡",
         "img": "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=600&h=400&fit=crop"},
        {"nome": "Contribuição para momentos especiais em família", "preco": "R$ 480", "emoji": "👨‍👩‍👧‍👦",
         "img": "https://images.unsplash.com/photo-1511895426328-dc8714191300?w=600&h=400&fit=crop"},
        {"nome": "Ajuda para realizarmos sonhos juntos", "preco": "R$ 1000", "emoji": "✨",
         "img": "https://images.unsplash.com/photo-1499209974431-9dddcece7f88?w=600&h=400&fit=crop"},
        {"nome": "Fundo \"lua de mel inesquecível\"", "preco": "R$ 850", "emoji": "🏝️",
         "img": "https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?w=600&h=400&fit=crop"},
        {"nome": "Contribuição para o caixa de reserva dos planos futuros", "preco": "R$ 700", "emoji": "📈",
         "img": "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=600&h=400&fit=crop"},
    ]

    if "presente_selecionado" not in st.session_state:
        st.session_state.presente_selecionado = None
    if "scroll_to_pix" not in st.session_state:
        st.session_state.scroll_to_pix = False

    COLUNAS = 3
    for i in range(0, len(presentes), COLUNAS):
        cols = st.columns(COLUNAS)
        for col, presente in zip(cols, presentes[i:i + COLUNAS]):
            with col:
                if presente["img"]:
                    st.markdown(f"""
                        <div style="
                            width: 100%;
                            padding-bottom: 66.5%;
                            position: relative;
                            overflow: hidden;
                            border-radius: 10px;
                            margin-bottom: 8px;
                        ">
                            <img src="{presente['img']}"
                                style="
                                    position: absolute;
                                    top: 0; left: 0;
                                    width: 100%;
                                    height: 100%;
                                    object-fit: cover;
                                "
                            />
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"<div style='font-size:52px;text-align:center;'>{presente['emoji']}</div>",
                        unsafe_allow_html=True
                    )

                # Bloco de texto com altura fixa — garante que o botão
                # sempre apareça na mesma linha vertical em cada row
                st.markdown(f"""
                    <div style="
                        height: 110px;
                        overflow: hidden;
                        display: flex;
                        flex-direction: column;
                        justify-content: flex-start;
                        margin-bottom: 6px;
                    ">
                        <p style="font-weight:bold; font-size:0.88rem; margin: 0 0 4px 0; line-height:1.4;">
                            {presente['nome']}
                        </p>
                        <p style="color:#888; font-size:0.82rem; margin:0;">
                            {presente['preco']}
                        </p>
                    </div>
                """, unsafe_allow_html=True)

                if st.button("Pagar com Pix 💛", key=f"pix_{i}_{presente['nome'][:10]}", use_container_width=True, type="primary"):
                    st.session_state.presente_selecionado = presente
                    st.session_state.scroll_to_pix = True
                    st.rerun()
    st.divider()
    st.markdown("<div id='pagamento_pix'></div>", unsafe_allow_html=True)

    # ── Área de pagamento Pix ──
    st.divider()
    # Âncora para rolagem
    st.markdown("<div id='pagamento_pix'></div>", unsafe_allow_html=True)

    if st.session_state.presente_selecionado:
        p = st.session_state.presente_selecionado
        
        # 1. Calculamos o valor AQUI, antes de tudo, para garantir que a variável exista!
        valor = parse_preco(p['preco'])
        
        with st.container(border=True):
            col_info, col_qr = st.columns([2, 1])
            
            with col_info:
                st.markdown("### 💛 Pagar via Pix")
                st.markdown("**Presente escolhido:**")
                st.markdown(f"{p['emoji']} {p['nome']}")
                st.markdown(f"**Valor sugerido:** {p['preco']}")
                st.markdown(f"**Chave Pix:** `{CHAVE_PIX}`")
                st.caption("Escaneie o QR Code ao lado pelo app do seu banco, ou copie o Pix Copia e Cola abaixo.")
                if st.button("✕ Fechar", key="fechar_popup"):
                    st.session_state.presente_selecionado = None
                    st.rerun()
                    
            with col_qr:
                try:
                    # 2. Agora usamos a variável 'valor' com segurança
                    qr_bytes, payload = gerar_qrcode_pix(CHAVE_PIX, valor)
                    st.image(qr_bytes, width=250, caption="Escaneie para pagar")
                except Exception as e:
                    payload = ""
                    st.warning(f"Erro ao gerar QR Code: {e}")

            if payload:
                st.markdown("**Pix Copia e Cola:**")
                st.code(payload, language=None)

        # Aciona rolagem JS até a âncora
        if st.session_state.scroll_to_pix:
            st.session_state.scroll_to_pix = False
            st.components.v1.html("""
                <script>
                    setTimeout(function() {
                        const doc = window.parent.document;
                        const el = doc.getElementById('pagamento_pix');
                        if (el) {
                            el.scrollIntoView({behavior: 'smooth', block: 'start'});
                        } else {
                            window.parent.scrollTo({
                                top: doc.body.scrollHeight,
                                behavior: 'smooth'
                            });
                        }
                    }, 200);
                </script>
            """, height=0)

    st.divider()


# ================================
# Endereço
# ================================
elif pagina == " Endereço dos Eventos":
    st.header(" Endereço e Informações")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Cerimônia")
        st.write(f"**Local:** {ENDERECO_CERIMONIA}")
        st.write(f"**Horário:** {HORARIO_CERIMONIA}")
        mapa_cerimonia = f"https://www.google.com/maps?q={urllib.parse.quote(ENDERECO_CERIMONIA)}&output=embed"
        st.components.v1.html(
            f'<iframe src="{mapa_cerimonia}" width="100%" height="350" style="border:0;" loading="lazy"></iframe>',
            height=370
        )
    with col2:
        st.subheader("Recepção")
        st.write(f"**Local:** {ENDERECO_FESTA}")
        st.write(f"**Horário:** {HORARIO_FESTA}")
        mapa_festa = f"https://www.google.com/maps?q={urllib.parse.quote(ENDERECO_FESTA)}&output=embed"
        st.components.v1.html(
            f'<iframe src="{mapa_festa}" width="100%" height="350" style="border:0;" loading="lazy"></iframe>',
            height=370
        )
    st.info("💡 Dica: Use um aplicativo de navegação para ver rotas, horários e trânsito no dia.")

# ================================
# Galeria de Fotos
# ================================
else:
    st.header(" Galeria de Fotos")
    st.write("Compartilhe suas fotos do casamento e veja as fotos de todos!")
    uploader = st.file_uploader(
        "Selecione suas imagens (PNG, JPG, JPEG)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True
    )
    nome_autor = st.text_input("Seu nome (para marcar as fotos)*")
    btn_upload = st.button("Enviar fotos", type="primary")

    if btn_upload:
        if not nome_autor.strip():
            st.error("Por favor, informe seu nome para marcar as fotos.")
        elif not uploader:
            st.error("Selecione ao menos uma imagem.")
        else:
            saved = 0
            for f in uploader:
                try:
                    ext = f.name.rsplit(".", 1)[-1].lower()
                    content_type = "image/png" if ext == "png" else "image/jpeg"
                    dados = f.getbuffer().tobytes()
                    base = slugify(f.name.rsplit(".", 1)[0])
                    salvar_foto(nome_autor.strip(), f"{base}.{ext}", dados, content_type)
                    saved += 1
                except Exception as e:
                    st.error(f"Falha ao salvar {f.name}: {e}")
            if saved > 0:
                st.success(f"✅ {saved} foto(s) enviada(s) com sucesso!")
                st.rerun()

    st.divider()
    st.subheader("Galeria")
    fotos_df = carregar_fotos()

    if len(fotos_df) == 0:
        st.info("Ainda não há fotos. Seja o primeiro a compartilhar!")
    else:
        page_size = st.slider("Fotos por página", 4, 20, 8, 2)
        total     = len(fotos_df)
        max_page  = max(1, (total - 1) // page_size + 1)
        page      = st.number_input("Página", min_value=1, max_value=max_page, value=1)
        start     = (page - 1) * page_size
        end       = start + page_size
        show      = fotos_df.iloc[start:end]
        for _, row in show.iterrows():
            st.image(row["url"], use_container_width=True)
            st.caption(f"📷 {row['autor']} — {human_time(row['timestamp'])}")
            st.divider()
        st.write(f"Total de fotos: {total}")

# -------------------------------
# Rodapé
# -------------------------------
st.divider()
st.write("Qualquer dúvida, entre em contato com os noivos. Obrigado por participar desse momento especial! 💍")