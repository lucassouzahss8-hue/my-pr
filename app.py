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

    # --- GERENCIAR RECEITAS ---
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

    # --- CONFIGURAÇÕES DO PRODUTO ---
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

    if df_ing.empty:
        st.warning("⚠️ Adicione ingredientes na aba 'Ingredientes' da sua planilha.")
        return

    # --- ÁREA DOS INGREDIENTES ---
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
            
            filtro_ing = df_ing[df_ing['nome'] == escolha]
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
    cmv_percentual = (v_cmv / preco_venda_produto * 100) if preco_venda_produto > 0 else 0
    cor_cmv = "#4ade80" if cmv_percentual <= 35 else "#facc15" if cmv_percentual <= 45 else "#f87171"

    # --- TABELA DETALHADA ---
    st.divider()
    res1, res2 = st.columns([1.5, 1])
    with res1:
        st.markdown(f"### Detalhamento: {nome_produto_final if nome_produto_final else 'Novo Produto'}")
        df_resumo = pd.DataFrame({
            "Item": ["Ingredientes", "Quebra", "Despesas Gerais", "Embalagem", "Custo Produção", "CMV (%)", "Lucro", "Entrega", "Taxas", "TOTAL FINAL"],
            "Valor": [f"R$ {custo_ingredientes_total:.2f}", f"R$ {v_quebra:.2f}", f"R$ {v_despesas:.2f}", f"R$ {valor_embalagem:.2f}", f"R$ {custo_total_prod:.2f}", f"{cmv_percentual:.1f}%", f"R$ {lucro_valor:.2f}", f"R$ {taxa_entrega:.2f}", f"R$ {v_taxa_financeira:.2f}", f"R$ {preco_venda_final:.2f}"]
        })
        st.table(df_resumo)
        if st.button("💾 Salvar Receita", use_container_width=True):
            if nome_produto_final:
                df_nova = pd.DataFrame(lista_para_salvar)
                df_final = pd.concat([df_rec[df_rec['nome_receita'] != nome_produto_final], df_nova], ignore_index=True)
                conn.update(worksheet="Receitas", data=df_final)
                st.success(f"Receita '{nome_produto_final}' salva!")
                st.rerun()

    with res2:
        st.markdown(f"<div class='resultado-box'><p style='margin:0; font-size:14px; opacity: 0.8;'>VALOR SUGERIDO</p><h2 style='margin:0;'>TOTAL ({forma_pagamento})</h2><h1 style='color: #60a5fa !important; font-size:48px;'>R$ {preco_venda_final:.2f}</h1><hr style='border-color: #4b5563;'><p><b>Lucro Líquido:</b> <span style='color: #4ade80;'>R$ {lucro_valor:.2f}</span></p><p><b>CMV:</b> <span style='color: {cor_cmv}; font-weight: bold;'>{cmv_percentual:.1f}%</span></p><p>Custo Produção: R$ {custo_total_prod:.2f}</p></div>", unsafe_allow_html=True)

    # ==========================================
    # --- SISTEMA DE ORÇAMENTOS (INTEGRADO) ---
    # ==========================================
    st.divider()
    st.markdown("<h2 class='titulo-planilha'>📋 Gerador de Orçamentos</h2>", unsafe_allow_html=True)
    tab_gerar, tab_salvos = st.tabs(["🆕 Criar Orçamento", "📂 Histórico"])

    with tab_gerar:
        c_cli1, c_cli2, c_cli3 = st.columns([2, 1, 1])
        nome_cliente = c_cli1.text_input("Nome do Cliente", placeholder="Maria Silva")
        tel_cliente = c_cli2.text_input("Telefone", placeholder="(00) 00000-0000")
        data_orc_input = c_cli3.date_input("Data do Orçamento", value=date.today())
        
        c_tax1, c_tax2, c_tax3 = st.columns([1, 1, 1])
        margem_orc = c_tax1.number_input("Margem de Lucro Orçamento (%)", value=margem_lucro)
        pag_orc = c_tax2.selectbox("Forma de Pagamento Orçamento", ["Crédito", "PIX"], index=0 if forma_pagamento=="Crédito" else 1)
        dist_orc = c_tax3.number_input("Distância KM (Orçamento)", min_value=0.0, value=distancia_km)

        nome_produto_grupo = st.text_input("📌 Nome do Produto (Grupo)", placeholder="Ex: Kit Festa Especial")

        st.divider()
        co1, co2, co3, co4 = st.columns([2, 1, 1, 1])
        item_sel = co1.selectbox("Selecione o Item da Planilha:", options=[""] + df_ing['nome'].tolist(), key="sel_item_orc")
        qtd_orc = co2.number_input("Qtd", min_value=1, value=1, key="qtd_item_orc")
        taxa_f_orc = co3.number_input("Frete Unit. (R$)", min_value=0.0, value=0.0)
        taxa_e_orc = co4.number_input("Emb. Unit. (R$)", min_value=0.0, value=0.0)

        if st.button("➕ Adicionar ao Grupo"):
            if item_sel != "" and nome_produto_grupo != "":
                filtro = df_ing[df_ing['nome'] == item_sel]
                if not filtro.empty:
                    p_unit_ing = float(filtro['preco'].iloc[0])
                    v_quebra_item = p_unit_ing * (perc_quebra / 100)
                    v_desp_item = p_unit_ing * (perc_despesas / 100)
                    custo_total_item = p_unit_ing + v_quebra_item + v_desp_item + taxa_e_orc
                    
                    st.session_state.carrinho_orc.append({
                        "Item": item_sel, 
                        "Qtd": qtd_orc, 
                        "Custo_Total_Unit": custo_total_item,
                        "Frete_Manual": taxa_f_orc
                    })
                    st.rerun()

        if st.session_state.carrinho_orc:
            st.markdown(f"### 📦 {nome_produto_grupo}")
            total_custo_grupo = 0.0
            total_frete_manual = 0.0

            for idx, it in enumerate(st.session_state.carrinho_orc):
                cols = st.columns([4, 1, 2, 0.5])
                sub_custo = it['Custo_Total_Unit'] * it['Qtd']
                total_custo_grupo += sub_custo
                total_frete_manual += (it['Frete_Manual'] * it['Qtd'])
                
                cols[0].write(f"🔹 {it['Item']}")
                cols[1].write(f"x{it['Qtd']}")
                cols[2].write(f"R$ {sub_custo:.2f}")
                if cols[3].button("❌", key=f"del_orc_{idx}"):
                    st.session_state.carrinho_orc.pop(idx)
                    st.rerun()
            
            # Cálculo final usando as taxas do precificador (sem exibir detalhes extras)
            preco_venda_itens = total_custo_grupo * (1 + (margem_orc / 100))
            taxa_entrega_orc = (dist_orc - km_gratis) * valor_por_km if dist_orc > km_gratis else 0.0
            total_frete_geral = total_frete_manual + taxa_entrega_orc
            t_perc_orc = (taxa_credito_input / 100) if pag_orc == "Crédito" else 0.0
            taxa_fin_orc = (preco_venda_itens + total_frete_geral) * t_perc_orc
            total_final_orc = preco_venda_itens + total_frete_geral + taxa_fin_orc

            st.markdown(f"## **TOTAL FINAL: R$ {total_final_orc:.2f}**")

            b1, b2, b3 = st.columns(3)
            if b1.button("📱 Texto WhatsApp", use_container_width=True):
                msg = f"*ORÇAMENTO: {nome_produto_grupo}*\nData: {data_orc_input.strftime('%d/%m/%Y')}\nCliente: {nome_cliente}\n" + "-"*20 + "\n"
                for i in st.session_state.carrinho_orc:
                    msg += f"• {i['Item']} (x{i['Qtd']})\n"
                msg += "-"*20 + f"\n*Valor Total: R$ {total_final_orc:.2f}* ({pag_orc})"
                st.code(msg, language="text")
            
            if b2.button("💾 Salvar Orçamento", use_container_width=True):
                df_s = pd.DataFrame([{"Data": data_orc_input.strftime('%d/%m/%Y'), "Cliente": nome_cliente, "Produto": nome_produto_grupo, "Total": f"R$ {total_final_orc:.2f}"}])
                conn.update(worksheet="Orcamentos_Salvos", data=pd.concat([carregar_orcamentos_salvos(), df_s], ignore_index=True))
                st.success("Salvo!")

            if b3.button("🗑️ Limpar", use_container_width=True):
                st.session_state.carrinho_orc = []
                st.rerun()

    with tab_salvos:
        st.dataframe(carregar_orcamentos_salvos(), use_container_width=True)

if __name__ == "__main__":
    main()
