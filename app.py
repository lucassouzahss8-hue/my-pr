import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date

# 1. Configuração da Página
st.set_page_config(
    page_title="Precificador Profissional", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Estilização CSS
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .titulo-planilha { 
        color: #1e3a8a; 
        font-weight: bold; 
        border-bottom: 2px solid #1e3a8a; 
        margin-bottom: 20px; 
        text-align: center;
    }
    .resultado-box { 
        background-color: #262730; 
        padding: 25px; 
        border-radius: 15px; 
        border-left: 10px solid #1e3a8a; 
        box-shadow: 2px 2px 15px rgba(0,0,0,0.3); 
        color: white; 
    }
    .resultado-box h1, .resultado-box h2, .resultado-box p, .resultado-box b { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO BANCO DE DADOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- INICIALIZAÇÃO DO ESTADO ---
if "n_itens" not in st.session_state:
    st.session_state.n_itens = 1
if "carrinho_orc" not in st.session_state:
    st.session_state.carrinho_orc = []

# --- FUNÇÕES DE CARREGAMENTO ---
def carregar_ingredientes():
    try:
        df = conn.read(worksheet="Ingredientes", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['nome', 'unidade', 'preco'])
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

def carregar_receitas_nuvem():
    try:
        df = conn.read(worksheet="Receitas", ttl=0)
        return df if df is not None else pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])
    except:
        return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])

# --- INÍCIO DO APP ---
df_ing = carregar_ingredientes()
df_rec = carregar_receitas_nuvem()

st.markdown("<h1 class='titulo-planilha'>📊 Precificador e Gestor de Orçamentos</h1>", unsafe_allow_html=True)

# --- SIDEBAR TAXAS ---
with st.sidebar:
    st.header("⚙️ Configurações")
    taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
    st.divider()
    km_gratis = st.number_input("KM Isentos", value=5)
    valor_por_km = st.number_input("R$ por KM adicional", value=2.0)

# --- TABELA DE PRECIFICAÇÃO (A BASE QUE VOCÊ PEDIU PARA MANTER) ---
st.subheader("🥣 Montagem da Receita / Produto")
col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
with col_p1:
    nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_prod_main")
with col_p2:
    margem_lucro_main = st.number_input("Margem de Lucro (%)", min_value=0, value=135, key="margem_main")
with col_p3:
    distancia_km_main = st.number_input("Distância para Entrega (km)", value=0.0, step=0.1, key="dist_main")
with col_p4:
    forma_pgto_main = st.selectbox("Forma de Pagamento", ["PIX", "Crédito"], key="pgto_main")

st.divider()

col_esq, col_dir = st.columns([2, 1])

with col_esq:
    st.markdown("#### 🛒 Ingredientes da Receita")
    n_itens = st.number_input("Quantos ingredientes?", min_value=1, value=st.session_state.n_itens)
    st.session_state.n_itens = n_itens
    
    custo_ingredientes_total = 0.0
    lista_para_salvar = []

    # Tabela dinâmica de ingredientes
    for i in range(int(n_itens)):
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
        with c1:
            escolha = st.selectbox(f"Item {i+1}", options=[""] + df_ing['nome'].tolist(), key=f"ing_{i}")
        
        filtro_ing = df_ing[df_ing['nome'] == escolha]
        if not filtro_ing.empty:
            dados_item = filtro_ing.iloc[0]
            with c2:
                qtd_u = st.number_input(f"Qtd", key=f"q_{i}", step=0.01, value=0.0)
            with c3:
                unid_u = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")

            # Cálculo de conversão
            fator = 1.0
            u_base = str(dados_item['unidade']).lower().strip()
            if unid_u == "g" and u_base == "kg": fator = 1/1000
            elif unid_u == "kg" and u_base == "g": fator = 1000
            
            custo_parcial = (qtd_u * fator) * float(dados_item['preco'])
            custo_ingredientes_total += custo_parcial
            lista_para_salvar.append({"nome_receita": nome_produto_final, "ingrediente": escolha, "qtd": qtd_u, "unid": unid_u})
            
            with c4:
                st.markdown(f"<p style='padding-top:35px;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

with col_dir:
    st.markdown("#### ⚙️ Adicionais de Produção")
    perc_quebra = st.slider("Quebra/Perda (%)", 0, 15, 2)
    perc_despesas = st.slider("Despesas Fixas (%)", 0, 100, 30)
    valor_embalagem = st.number_input("Embalagem Individual (R$)", value=0.0)

# --- CÁLCULOS TÉCNICOS ---
v_quebra = custo_ingredientes_total * (perc_quebra / 100)
v_despesas = custo_ingredientes_total * (perc_despesas / 100)
custo_total_producao = custo_ingredientes_total + v_quebra + v_despesas + valor_embalagem
preco_sugerido = custo_total_producao * (1 + (margem_lucro_main / 100))

# --- RESULTADO DO PRECIFICADOR ---
st.divider()
res_c1, res_c2 = st.columns([1.5, 1])
with res_c1:
    st.markdown(f"### Detalhes de Fábrica: {nome_produto_final}")
    detalhe = pd.DataFrame({
        "Descrição": ["Total Ingredientes", "Custo de Quebra", "Despesas Gerais", "Embalagem", "CUSTO PRODUÇÃO"],
        "Valor": [f"R$ {custo_ingredientes_total:.2f}", f"R$ {v_quebra:.2f}", f"R$ {v_despesas:.2f}", f"R$ {valor_embalagem:.2f}", f"R$ {custo_total_producao:.2f}"]
    })
    st.table(detalhe)
    if st.button("💾 Salvar esta Receita na Nuvem"):
        if nome_produto_final:
            df_nova = pd.DataFrame(lista_para_salvar)
            conn.update(worksheet="Receitas", data=pd.concat([df_rec, df_nova], ignore_index=True))
            st.success("Receita Salva!")

with res_c2:
    st.markdown(f"<div class='resultado-box'><p>PREÇO SUGERIDO UNITÁRIO</p><h1>R$ {preco_sugerido:.2f}</h1><p>Lucro Estimado: R$ {(preco_sugerido - custo_total_producao):.2f}</p></div>", unsafe_allow_html=True)

# --- GERADOR DE ORÇAMENTOS (ATUALIZADO E CORRIGIDO) ---
st.markdown("<h2 class='titulo-planilha'>📋 Gerador de Orçamentos para Clientes</h2>", unsafe_allow_html=True)

# Interface do Orçamento
o1, o2, o3 = st.columns([2, 1, 1])
item_orc = o1.selectbox("Adicionar Item ao Orçamento:", options=[""] + df_ing['nome'].tolist(), key="add_item_orc")
qtd_orc = o2.number_input("Qtd Itens", min_value=1, value=1)
if o3.button("➕ Adicionar ao Pedido", use_container_width=True):
    if item_orc:
        filtro = df_ing[df_ing['nome'] == item_orc]
        if not filtro.empty:
            p_puro = float(filtro['preco'].iloc[0])
            st.session_state.carrinho_orc.append({
                "item": item_orc, "qtd": qtd_orc, "custo_unit": p_puro
            })
            st.rerun()

if st.session_state.carrinho_orc:
    total_venda_orc = 0.0
    total_custo_orc = 0.0
    
    # Tabela de visualização do Orçamento
    st.markdown("#### Itens Selecionados")
    cols_h = st.columns([3, 1, 1.5, 1.5, 2, 0.5])
    cols_h[0].write("**Produto**")
    cols_h[1].write("**Qtd**")
    cols_h[2].write("**Unit. Puro**") # Valor de custo original
    cols_h[3].write("**Unit. Venda**") # Valor com lucro
    cols_h[4].write("**Subtotal**")

    for idx, it in enumerate(st.session_state.carrinho_orc):
        c = st.columns([3, 1, 1.5, 1.5, 2, 0.5])
        
        # Cálculos (Evitando KeyError usando nomes fixos)
        v_unit_venda = it['custo_unit'] * (1 + (margem_lucro_main / 100))
        sub_venda = v_unit_venda * it['qtd']
        
        total_custo_orc += (it['custo_unit'] * it['qtd'])
        total_venda_orc += sub_venda
        
        c[0].write(f"🔹 {it['item']}")
        c[1].write(f"x{it['qtd']}")
        c[2].write(f"R$ {it['custo_unit']:.2f}") # UNITÁRIO PURO
        c[3].write(f"R$ {v_unit_venda:.2f}")
        c[4].write(f"**R$ {sub_venda:.2f}**")
        
        if c[5].button("❌", key=f"del_{idx}"):
            st.session_state.carrinho_orc.pop(idx)
            st.rerun()

    # Totais Finais do Orçamento
    st.divider()
    f_dist = (distancia_km_main - km_gratis) * valor_por_km if distancia_km_main > km_gratis else 0.0
    t_cartao = (total_venda_orc + f_dist) * (taxa_credito_input / 100) if forma_pgto_main == "Crédito" else 0.0
    total_final = total_venda_orc + f_dist + t_cartao

    final1, final2 = st.columns(2)
    with final1:
        st.write(f"📦 Total Custo de Fábrica: R$ {total_custo_orc:.2f}")
        st.write(f"🚚 Entrega: R$ {f_dist:.2f}")
    with final2:
        if forma_pgto_main == "Crédito":
            st.write(f"💳 Taxa ({taxa_credito_input}%): R$ {t_cartao:.2f}")
        st.markdown(f"### 🏁 TOTAL FINAL: R$ {total_final:.2f}")

if __name__ == "__main__":
    pass
