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
if "nome_prod" not in st.session_state:
    st.session_state.nome_prod = ""
if "carrinho_orc" not in st.session_state:
    st.session_state.carrinho_orc = []

# --- FUNÇÕES DE DADOS ---
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

def carregar_orcamentos_salvos():
    try:
        df = conn.read(worksheet="Orcamentos_Salvos", ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- APP PRINCIPAL ---
def main():
    df_ing = carregar_ingredientes()
    df_rec = carregar_receitas_nuvem()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador</h1>", unsafe_allow_html=True)

    # --- SIDEBAR: AJUSTE DE TAXAS ---
    with st.sidebar:
        st.header("⚙️ Ajuste de Taxas")
        taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
        st.divider()
        km_gratis = st.number_input("KM Isentos", value=5)
        valor_por_km = st.number_input("R$ por KM adicional", value=2.0, step=0.1)

    # --- CONFIGURAÇÕES DO PRODUTO (PRECIFICADOR) ---
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1:
        nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_prod")
    with col_p2:
        margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=135)
    with col_p3:
        distancia_km = st.number_input("Distância (km)", min_value=0.0, value=0.0, step=0.1)
    with col_p4:
        forma_pagamento = st.selectbox("Pagamento", ["Crédito", "PIX"])
        
    st.divider()

    # (Área de Ingredientes e Adicionais mantida conforme original...)
    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens_input = st.number_input("Número de itens:", min_value=1, key="n_itens")
        custo_ingredientes_total = 0.0
        lista_para_salvar = []

        for i in range(int(n_itens_input)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1:
                lista_nomes = df_ing['nome'].tolist() if not df_ing.empty else []
                idx_def = 0
                if f"nome_{i}" in st.session_state and st.session_state[f"nome_{i}"] in lista_nomes:
                    idx_def = lista_nomes.index(st.session_state[f"nome_{i}"])
                escolha = st.selectbox(f"Item {i+1}", options=lista_nomes, key=f"nome_{i}", index=idx_def)
            
            filtro_ing = df_ing[df_ing['nome'] == escolha] if not df_ing.empty else pd.DataFrame()
            if not filtro_ing.empty:
                dados_item = filtro_ing.iloc[0]
                with c2:
                    qtd_usada = st.number_input(f"Qtd", key=f"qtd_{i}", step=0.01, value=st.session_state.get(f"qtd_{i}", 0.0))
                with c3:
                    unid_uso = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")

                fator = 1.0
                u_base = str(dados_item['unidade']).lower().strip()
                if unid_uso == "g" and u_base == "kg": fator = 1/1000
                elif unid_uso == "kg" and u_base == "g": fator = 1000
                elif unid_uso == "ml" and u_base == "l": fator = 1/1000
                
                custo_parcial = (qtd_usada * fator) * float(dados_item['preco'])
                custo_ingredientes_total += custo_parcial
                lista_para_salvar.append({"nome_receita": nome_produto_final, "ingrediente": escolha, "qtd": qtd_usada, "unid": unid_uso})
                with c4:
                    st.markdown(f"<p style='padding-top:35px; font-weight:bold;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

    with col_dir:
        st.subheader("⚙️ Adicionais")
        perc_quebra = st.slider("Quebra (%)", 0, 15, 2)
        perc_despesas = st.slider("Despesas Gerais (%)", 0, 100, 30)
        valor_embalagem = st.number_input("Embalagem (R$)", min_value=0.0, value=0.0)

    # --- CÁLCULOS FINAIS ---
    taxa_entrega = (distancia_km - km_gratis) * valor_por_km if distancia_km > km_gratis else 0.0
    v_quebra = custo_ingredientes_total * (perc_quebra / 100)
    v_despesas = custo_ingredientes_total * (perc_despesas / 100)
    v_cmv = custo_ingredientes_total + v_quebra + valor_embalagem
    custo_total_prod = v_cmv + v_despesas
    lucro_valor = custo_total_prod * (margem_lucro / 100)
    preco_venda_produto = custo_total_prod + lucro_valor
    t_percentual = (taxa_credito_input / 100) if forma_pagamento == "Crédito" else 0.0
    v_taxa_financeira = (preco_venda_produto + taxa_entrega) * t_percentual
    preco_venda_final = preco_venda_produto + taxa_entrega + v_taxa_financeira

    # ==========================================
    # --- GERADOR DE ORÇAMENTOS (CORRIGIDO) ---
    # ==========================================
    st.divider()
    st.markdown("<h2 class='titulo-planilha'>📋 Gerador de Orçamentos</h2>", unsafe_allow_html=True)
    tab_gerar, tab_salvos = st.tabs(["🆕 Criar Orçamento", "📂 Histórico"])

    with tab_gerar:
        c_cli1, c_cli2, c_cli3 = st.columns([2, 1, 1])
        nome_cliente = c_cli1.text_input("Nome do Cliente", placeholder="Maria Silva")
        tel_cliente = c_cli2.text_input("Telefone", placeholder="(00) 00000")
        data_orc_input = c_cli3.date_input("Data", value=date.today())
        nome_produto_grupo = st.text_input("📌 Nome do Pedido/Grupo", placeholder="Ex: Kit Festa 01")

        st.divider()
        co1, co2, co3, co4 = st.columns([3, 1, 1, 1])
        item_sel = co1.selectbox("Selecione Item:", options=[""] + df_ing['nome'].tolist(), key="sel_item_orc")
        qtd_orc = co2.number_input("Qtd", min_value=1, value=1, key="qtd_item_orc")
        f_orc = co3.number_input("Frete (R$)", min_value=0.0, value=0.0, key="f_orc")
        e_orc = co4.number_input("Emb. (R$)", min_value=0.0, value=0.0, key="e_orc")

        if st.button("➕ Adicionar Item"):
            if item_sel != "" and nome_produto_grupo != "":
                filtro = df_ing[df_ing['nome'] == item_sel]
                if not filtro.empty:
                    p_base = float(filtro['preco'].iloc[0])
                    v_q = p_base * (perc_quebra / 100)
                    v_d = p_base * (perc_despesas / 100)
                    custo_u = p_base + v_q + v_d + f_orc + e_orc
                    
                    st.session_state.carrinho_orc.append({
                        "Item": item_sel, "Qtd": qtd_orc, 
                        "Custo_U": custo_u, "Frete": f_orc, "Emb": e_orc
                    })
                    st.rerun()

        if st.session_state.carrinho_orc:
            st.markdown(f"### 📦 {nome_produto_grupo}")
            total_venda_itens = 0.0

            for idx, it in enumerate(st.session_state.carrinho_orc):
                cols = st.columns([3, 1, 1, 1, 2, 0.5])
                # Proteção .get() para evitar KeyError se houver lixo no session_state
                qtd = it.get('Qtd', 1)
                custo_u = it.get('Custo_U', 0.0)
                frete = it.get('Frete', 0.0)
                emb = it.get('Emb', 0.0)
                
                venda_u = custo_u * (1 + (margem_lucro / 100))
                subtotal = venda_u * qtd
                total_venda_itens += subtotal
                
                cols[0].write(f"🔹 {it.get('Item', 'Item')}")
                cols[1].write(f"x{qtd}")
                cols[2].write(f"F: R${frete:.2f}")
                cols[3].write(f"E: R${emb:.2f}")
                cols[4].write(f"**R$ {subtotal:.2f}**")
                if cols[5].button("❌", key=f"del_{idx}"):
                    st.session_state.carrinho_orc.pop(idx)
                    st.rerun()

            # Totais finais com taxas da sidebar
            v_entrega = (distancia_km - km_gratis) * valor_por_km if distancia_km > km_gratis else 0.0
            taxa_f = (total_venda_itens + v_entrega) * (taxa_credito_input/100) if forma_pagamento == "Crédito" else 0.0
            total_geral = total_venda_itens + v_entrega + taxa_f

            st.markdown(f"## **TOTAL: R$ {total_geral:.2f}**")

            b1, b2, b3 = st.columns(3)
            if b1.button("📱 Texto WhatsApp", use_container_width=True):
                msg = (
                    f"✨ *ORÇAMENTO: {nome_produto_grupo}* ✨\n\n"
                    f"📅 *Data:* {data_orc_input.strftime('%d/%m/%Y')}\n"
                    f"👤 *Cliente:* {nome_cliente}\n\n"
                    f"--- *ITENS* ---\n"
                )
                for i in st.session_state.carrinho_orc:
                    msg += f"✅ {i.get('Item')} (x{i.get('Qtd')})\n"
                
                msg += (
                    f"\n--- *TOTAL* ---\n"
                    f"💰 *Valor:* R$ {total_geral:.2f}\n"
                    f"💳 *Pagamento:* {forma_pagamento}\n\n"
                    f"Aguardamos seu retorno! 😊"
                )
                st.code(msg, language="text")
            
            if b2.button("💾 Salvar", use_container_width=True):
                df_s = pd.DataFrame([{"Data": data_orc_input.strftime('%d/%m/%Y'), "Cliente": nome_cliente, "Produto": nome_produto_grupo, "Total": f"R$ {total_geral:.2f}"}])
                conn.update(worksheet="Orcamentos_Salvos", data=pd.concat([carregar_orcamentos_salvos(), df_s], ignore_index=True))
                st.success("Salvo!")

            if b3.button("🗑️ Limpar Tudo", use_container_width=True):
                st.session_state.carrinho_orc = []
                st.rerun()

    with tab_salvos:
        st.dataframe(carregar_orcamentos_salvos(), use_container_width=True)

if __name__ == "__main__":
    main()
