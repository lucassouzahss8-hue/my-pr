import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página
st.set_page_config(
    page_title="Precificador Cloud", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Estilização CSS (Removido header hidden para a flecha aparecer)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .titulo-planilha { color: #1e3a8a; font-weight: bold; border-bottom: 2px solid #1e3a8a; margin-bottom: 20px; text-align: center; }
    .resultado-box { background-color: #262730; padding: 25px; border-radius: 15px; border-left: 10px solid #1e3a8a; color: white; }
    .resultado-box h1, .resultado-box h2, .resultado-box p, .resultado-box b { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. Conexão com Google Sheets
# Importante: No Streamlit Cloud, adicione o link da planilha em "Secrets"
url = "COLE_AQUI_O_LINK_DA_SUA_PLANILHA_GOOGLE"
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_ingredientes():
    try:
        df = pd.read_csv("ingredientes.csv")
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

def carregar_receitas_nuvem():
    try:
        return conn.read(spreadsheet=url)
    except:
        return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Ajuste de Taxas")
    taxa_debito = st.number_input("Taxa Débito (%)", value=1.99)
    taxa_credito = st.number_input("Taxa Crédito (%)", value=4.99)
    km_gratis = st.number_input("KM Isentos", value=5)
    valor_km = st.number_input("R$ por KM adicional", value=2.0)

# --- APP PRINCIPAL ---
def main():
    df_ing = carregar_ingredientes()
    df_rec = carregar_receitas_nuvem()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador Cloud</h1>", unsafe_allow_html=True)

    # Abrir/Deletar Receitas
    with st.expander("📂 Abrir Receitas Salvas na Nuvem"):
        receitas_nomes = df_rec['nome_receita'].unique().tolist() if not df_rec.empty else []
        receita_sel = st.selectbox("Selecione:", [""] + receitas_nomes)
        if st.button("🔄 Carregar"):
            if receita_sel:
                dados = df_rec[df_rec['nome_receita'] == receita_sel]
                st.session_state.nome_prod = receita_sel
                st.rerun()

    # Inputs Produto
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    nome_prod = c1.text_input("Produto:", key="nome_prod")
    margem = c2.number_input("Margem (%)", value=150)
    distancia = c3.number_input("Distância (km)", value=0.0)
    pagamento = c4.selectbox("Pagamento", ["PIX", "Débito", "Crédito"])

    st.divider()

    # Ingredientes
    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        n_itens = st.number_input("Itens:", min_value=1, value=1)
        custo_materiais = 0.0
        lista_save = []
        for i in range(int(n_itens)):
            cc1, cc2, cc3, cc4 = st.columns([3, 1, 1, 1.5])
            item = cc1.selectbox(f"Item {i+1}", df_ing['nome'].tolist(), key=f"item_{i}")
            # Correção do erro da imagem: garantindo que val_q exista
            qtd = cc2.number_input(f"Qtd", key=f"q_{i}", value=0.0)
            unid = cc3.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")
            
            # Cálculo de custo (simplificado para o exemplo)
            row = df_ing[df_ing['nome'] == item].iloc[0]
            preco_base = row['preco']
            custo_item = qtd * preco_base # Adicione sua lógica de fator g/kg aqui
            custo_materiais += custo_item
            cc4.write(f"R$ {custo_item:.2f}")
            lista_save.append({"nome_receita": nome_prod, "ingrediente": item, "qtd": qtd, "unid": unid})

    with col_dir:
        quebra = st.slider("Quebra (%)", 0, 15, 5)
        fixos = st.slider("Fixos (%)", 0, 100, 30)
        embalagem = st.number_input("Embalagem (R$)", value=0.0)

    # Cálculos e CMV
    v_quebra = custo_materiais * (quebra/100)
    cmv_valor = custo_materiais + v_quebra + embalagem
    preco_s_entrega = (cmv_valor + (custo_materiais * fixos/100)) * (1 + margem/100)
    
    perc_cmv = (cmv_valor / preco_s_entrega * 100) if preco_s_entrega > 0 else 0.0
    cor_cmv = "#4ade80" if perc_cmv <= 35 else "#facc15" if perc_cmv <= 45 else "#f87171"

    # Mostrar Resultado
    st.divider()
    res1, res2 = st.columns([1, 1])
    with res2:
        st.markdown(f"""
        <div class='resultado-box'>
            <h2>TOTAL A COBRAR</h2>
            <h1 style='color: #60a5fa !important;'>R$ {preco_s_entrega:.2f}</h1>
            <p>CMV: <span style='color:{cor_cmv}; font-weight: bold;'>{perc_cmv:.1f}%</span></p>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("💾 Salvar na Nuvem"):
        df_novo = pd.DataFrame(lista_save)
        df_final = pd.concat([df_rec, df_novo], ignore_index=True)
        conn.update(spreadsheet=url, data=df_final)
        st.success("Salvo no Google Sheets!")

if __name__ == "__main__":
    main()
