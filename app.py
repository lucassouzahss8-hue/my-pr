import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date

# 1. Configuração da Página
st.set_page_config(
    page_title="Precificador", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Estilização CSS Original (MANTIDA)
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
if "nome_prod" not in st.session_state:
    st.session_state.nome_prod = ""
if "carrinho_orcamento" not in st.session_state:
    st.session_state.carrinho_orcamento = []

# --- FUNÇÕES DE DADOS (MANTIDAS) ---
def carregar_ingredientes():
    try:
        df = conn.read(worksheet="Ingredientes", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['nome', 'unidade', 'preco'])
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

def carregar_receitas_nuvem():
    try:
        df = conn.read(worksheet="Receitas", ttl=0)
        if df is None or df.empty or 'nome_receita' not in df.columns:
            return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])
        return df
    except Exception:
        return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])

# --- FUNÇÃO EXCLUSIVA PARA O ORÇAMENTO (CALCULA PREÇO SEM CARREGAR NA TELA) ---
def calcular_preco_receita_salva(nome_receita, df_ing, df_rec, margem, quebra, despesas, embalagem, tx_credito):
    dados_rec = df_rec[df_rec['nome_receita'] == nome_receita]
    custo_total = 0.0
    for row in dados_rec.itertuples():
        ing = df_ing[df_ing['nome'] == row.ingrediente]
        if not ing.empty:
            preco_base = float(ing.iloc[0]['preco'])
            u_base = str(ing.iloc[0]['unidade']).lower().strip()
            fator = 1.0
            if row.unid == "g" and u_base == "kg": fator = 1/1000
            elif row.unid == "kg" and u_base == "g": fator = 1000
            elif row.unid == "ml" and u_base == "l": fator = 1/1000
            custo_total += (float(row.qtd) * fator) * preco_base
    
    v_quebra = custo_total * (quebra / 100)
    v_despesas = custo_total * (despesas / 100)
    v_cmv = custo_total + v_quebra + embalagem
    custo_prod = v_cmv + v_despesas
    preco_venda = custo_prod + (custo_prod * (margem / 100))
    # Aplica taxa financeira se houver
    preco_final = preco_venda / (1 - (tx_credito / 100)) if tx_credito > 0 else preco_venda
    return preco_final

# --- APP PRINCIPAL ---
def main():
    df_ing = carregar_ingredientes()
    df_rec = carregar_receitas_nuvem()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador</h1>", unsafe_allow_html=True)

    # --- TODO O SEU CÓDIGO ORIGINAL DE PRECIFICAÇÃO (SEM ALTERAÇÕES) ---
    with st.sidebar:
        st.header("⚙️ Ajuste de Taxas")
        taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
        st.divider()
        km_gratis = st.number_input("KM Isentos", value=5)
        valor_por_km = st.number_input("R$ por KM adicional", value=2.0, step=0.1)

    with st.expander("📂 Abrir ou Deletar Receitas Salvas"):
        receitas_nomes = df_rec['nome_receita'].unique().tolist() if not df_rec.empty else []
        col_rec1, col_rec2 = st.columns([3, 1])
        with col_rec1:
            receita_selecionada = st.selectbox("Selecione uma receita:", [""] + receitas_nomes)
        with col_rec2:
            st.write("") 
            if st.button("🔄 Carregar", use_container_width=True) and receita_selecionada != "":
                dados_rec = df_rec[df_rec['nome_receita'] == receita_selecionada]
                st.session_state.nome_prod = receita_selecionada
                st.session_state.n_itens = len(dados_rec)
                for idx, row in enumerate(dados_rec.itertuples()):
                    st.session_state[f"nome_{idx}"] = row.ingrediente
                    st.session_state[f"qtd_{idx}"] = float(row.qtd)
                    st.session_state[f"u_{idx}"] = row.unid
                st.rerun()

    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1: nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_prod")
    with col_p2: margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=135)
    with col_p3: distancia_km = st.number_input("Distância (km)", min_value=0.0, value=0.0, step=0.1)
    with col_p4: forma_pagamento = st.selectbox("Pagamento", ["Crédito", "PIX"])
    st.divider()

    if df_ing.empty:
        st.warning("⚠️ Adicione ingredientes na planilha.")
        return

    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens_input = st.number_input("Número de itens:", min_value=1, key="n_itens")
        custo_ingredientes_total = 0.0
        lista_para_salvar = []
        for i in range(int(n_itens_input)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1:
                lista_nomes = df_ing['nome'].tolist()
                idx_def = 0
                if f"nome_{i}" in st.session_state and st.session_state[f"nome_{i}"] in lista_nomes:
                    idx_def = lista_nomes.index(st.session_state[f"nome_{i}"])
                escolha = st.selectbox(f"Item {i+1}", options=lista_nomes, key=f"nome_{i}", index=idx_def)
            dados_item = df_ing[df_ing['nome'] == escolha].iloc[0]
            with c2: qtd_usada = st.number_input(f"Qtd", key=f"qtd_{i}", step=0.01, value=st.session_state.get(f"qtd_{i}", 0.0))
            with c3: unid_uso = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")
            fator = 1.0
            u_base = str(dados_item['unidade']).lower().strip()
            if unid_uso == "g" and u_base == "kg": fator = 1/1000
            elif unid_uso == "kg" and u_base == "g": fator = 1000
            elif unid_uso == "ml" and u_base == "l": fator = 1/1000
            custo_parcial = (float(qtd_usada) * fator) * float(dados_item['preco'])
            custo_ingredientes_total += custo_parcial
            lista_para_salvar.append({"nome_receita": nome_produto_final, "ingrediente": escolha, "qtd": qtd_usada, "unid": unid_uso})
            with c4: st.markdown(f"<p style='padding-top:35px; font-weight:bold;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

    with col_dir:
        st.subheader("⚙️ Adicionais")
        perc_quebra = st.slider("Quebra (%)", 0, 15, 2)
        perc_despesas = st.slider("Despesas Gerais (%)", 0, 100, 30)
        valor_embalagem = st.number_input("Embalagem (R$)", min_value=0.0, value=0.0)

    taxa_entrega_base = (distancia_km - km_gratis) * valor_por_km if distancia_km > km_gratis else 0.0
    v_quebra = custo_ingredientes_total * (perc_quebra / 100)
    v_despesas = custo_ingredientes_total * (perc_despesas / 100)
    v_cmv = custo_ingredientes_total + v_quebra + valor_embalagem
    custo_total_prod = v_cmv + v_despesas
    lucro_valor = custo_total_prod * (margem_lucro / 100)
    preco_venda_produto = custo_total_prod + lucro_valor
    t_percentual = (taxa_credito_input / 100) if forma_pagamento == "Crédito" else 0.0
    v_taxa_financeira = (preco_venda_produto + taxa_entrega_base) * t_percentual
    preco_venda_final = preco_venda_produto + taxa_entrega_base + v_taxa_financeira

    st.divider()
    res1, res2 = st.columns([1.5, 1])
    with res1:
        st.markdown(f"### Detalhamento")
        df_resumo = pd.DataFrame({
            "Item": ["Custo Produção", "Lucro", "Entrega", "Taxas", "TOTAL FINAL"],
            "Valor": [f"R$ {custo_total_prod:.2f}", f"R$ {lucro_valor:.2f}", f"R$ {taxa_entrega_base:.2f}", f"R$ {v_taxa_financeira:.2f}", f"R$ {preco_venda_final:.2f}"]
        })
        st.table(df_resumo)
        if st.button("💾 Salvar Receita", use_container_width=True):
            if nome_produto_final:
                df_nova = pd.DataFrame(lista_para_salvar)
                df_final = pd.concat([df_rec[df_rec['nome_receita'] != nome_produto_final], df_nova], ignore_index=True)
                conn.update(worksheet="Receitas", data=df_final)
                st.success("Salvo!")
                st.rerun()

    with res2:
        st.markdown(f"<div class='resultado-box'><h2>TOTAL SUGERIDO</h2><h1 style='color:#60a5fa!important;'>R$ {preco_venda_final:.2f}</h1></div>", unsafe_allow_html=True)

    # --- NOVA SEÇÃO: ORÇAMENTO MULTI-ITENS (SEM PRECISAR CARREGAR) ---
    st.divider()
    st.header("📝 Gerador de Orçamento Profissional")
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1: cliente_orc = st.text_input("Cliente", key="cli_nome")
        with c2: tel_orc = st.text_input("WhatsApp", key="cli_tel")
        with c3: data_orc = st.date_input("Data", value=date.today())

        st.markdown("### 🛒 Adicionar Itens ao Orçamento")
        col_sel, col_qtd, col_add = st.columns([3, 1, 1])
        with col_sel:
            receita_para_orc = st.selectbox("Selecione a Receita Salva:", [""] + receitas_nomes, key="sel_multi_orc")
        with col_qtd:
            qtd_para_orc = st.number_input("Qtd", min_value=1, value=1)
        with col_add:
            st.write("")
            if st.button("➕ Adicionar", use_container_width=True):
                if receita_para_orc:
                    # Calcula o preço da receita selecionada em tempo real, sem carregar na tela
                    p_unit = calcular_preco_receita_salva(receita_para_orc, df_ing, df_rec, margem_lucro, perc_quebra, perc_despesas, valor_embalagem, taxa_credito_input if forma_pagamento=="Crédito" else 0)
                    st.session_state.carrinho_orcamento.append({
                        "produto": receita_para_orc,
                        "qtd": qtd_orc,
                        "unitario": p_unit,
                        "subtotal": p_unit * qtd_para_orc
                    })
                    st.toast(f"{receita_para_orc} adicionado!")

    if st.session_state.carrinho_orcamento:
        st.markdown("---")
        st.subheader("Resumo do Pedido")
        df_carrinho = pd.DataFrame(st.session_state.carrinho_orcamento)
        st.table(df_carrinho.style.format({"unitario": "R$ {:.2f}", "subtotal": "R$ {:.2f}"}))
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1: taxa_f = st.number_input("Taxa de Entrega Final (R$)", value=taxa_entrega_base)
        with col_f2: emb_f = st.number_input("Embalagem Extra (R$)", value=0.0)
        
        total_geral = df_carrinho["subtotal"].sum() + taxa_f + emb_f
        st.markdown(f"## **TOTAL DO ORÇAMENTO: R$ {total_geral:.2f}**")

        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("🗑️ Limpar Tudo", use_container_width=True):
                st.session_state.carrinho_orcamento = []
                st.rerun()
        with c_btn2:
            if st.button("📲 Gerar Texto WhatsApp", use_container_width=True):
                itens_texto = ""
                for item in st.session_state.carrinho_orcamento:
                    itens_texto += f"• {item['produto']} ({item['qtd']}x) - R$ {item['subtotal']:.2f}\n"
                
                texto_zap = f"""
📋 *ORÇAMENTO*
📅 Data: {data_orc.strftime('%d/%m/%Y')}
👤 Cliente: {cliente_orc}
--------------------------
{itens_texto}
🚚 *Entrega:* R$ {taxa_f:.2f}
🛍️ *Adicionais:* R$ {emb_f:.2f}
--------------------------
✅ *TOTAL: R$ {total_geral:.2f}*
"""
                st.code(texto_zap, language="text")

if __name__ == "__main__":
    main()
