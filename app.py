import streamlit as st

import pandas as pd

from streamlit_gsheets import GSheetsConnection

from datetime import date

from fpdf import FPDF



# 1. Configuracao da Pagina

st.set_page_config(

    page_title="Precificador", 

    page_icon="📊", 

    layout="wide",

    initial_sidebar_state="collapsed"

)



# 2. Estilizacao CSS + PWA + Ajustes Mobile

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

    

    @media (max-width: 640px) {

        .stButton button {

            width: 100%;

            height: 48px;

            margin-bottom: 5px;

        }

        .titulo-planilha { font-size: 24px; }

    }

    </style>

    """, unsafe_allow_html=True)



conn = st.connection("gsheets", type=GSheetsConnection)



# Inicializacao de estados

if "carrinho_orc" not in st.session_state:

    st.session_state.carrinho_orc = []

if "n_itens_receita" not in st.session_state:

    st.session_state.n_itens_receita = 1

if "versao_lista" not in st.session_state:

    st.session_state.versao_lista = 0



# Funções de carregamento (Originais)

def carregar_ingredientes():

    try:

        df = conn.read(worksheet="Ingredientes", ttl=1)

        if df is None or df.empty:

            return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

        df.columns = [str(c).strip().lower() for c in df.columns]

        return df

    except:

        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])



def carregar_receitas_nuvem():

    try:

        df = conn.read(worksheet="Receitas", ttl=1)

        return df if df is not None else pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])

    except:

        return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])



def carregar_historico_orc():

    try:

        df = conn.read(worksheet="Orcamentos_Salvos", ttl=1)

        if df is not None:

            df.columns = [c.replace(" ", "_") for c in df.columns]

            return df

        return pd.DataFrame(columns=['Data', 'Cliente', 'Pedido', 'Valor_Final'])

    except:

        return pd.DataFrame(columns=['Data', 'Cliente', 'Pedido', 'Valor_Final'])



def exportar_pdf(cliente, pedido, itens, total):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", 'B', 16)

    pdf.cell(200, 10, "ORCAMENTO DETALHADO", ln=True, align='C')

    pdf.ln(10)

    pdf.set_font("Arial", '', 12)

    pdf.cell(200, 10, f"Cliente: {cliente}", ln=True)

    pdf.cell(200, 10, f"Pedido: {pedido}", ln=True)

    pdf.cell(200, 10, f"Data: {date.today().strftime('%d/%m/%Y')}", ln=True)

    pdf.ln(5)

    pdf.set_fill_color(30, 58, 138)

    pdf.set_text_color(255, 255, 255)

    pdf.cell(100, 10, " Produto", border=1, fill=True)

    pdf.cell(40, 10, " Qtd", border=1, fill=True)

    pdf.cell(50, 10, " Valor Total", border=1, fill=True, ln=True)

    pdf.set_text_color(0, 0, 0)

    for it in itens:

        pdf.cell(100, 10, f" {it['nome']}", border=1)

        pdf.cell(40, 10, f" {it['qtd']}", border=1)

        pdf.cell(50, 10, f" R$ {it['venda']:.2f}", border=1, ln=True)

    pdf.ln(5)

    pdf.set_font("Arial", 'B', 14)

    pdf.cell(200, 10, f"TOTAL FINAL: R$ {total:.2f}", ln=True, align='R')

    return pdf.output(dest='S').encode('latin-1', 'replace')



def adicionar_ao_carrinho():

    nome = st.session_state.sel_orc_it

    qtd = st.session_state.q_orc_input

    if nome != "":

        df_ing = carregar_ingredientes()

        p_unit_puro = float(df_ing[df_ing['nome'] == nome]['preco'].iloc[0])

        st.session_state.carrinho_orc.append({"nome": nome, "qtd": qtd, "preco_puro": p_unit_puro})



@st.fragment

def secao_orcamento(df_ing, margem_lucro, taxa_credito_input, forma_pagamento):

    st.divider()

    st.markdown("<h2 class='titulo-planilha'>📋 Gerador de Orçamentos</h2>", unsafe_allow_html=True)

    t1, t2 = st.tabs(["🆕 Criar Novo", "📂 Salvos"])

    with t1:

        c_cli1, c_cli2, c_cli3 = st.columns([2, 1, 1])

        nome_cliente = c_cli1.text_input("Nome do Cliente", key="cli_orc")

        tel_cliente = c_cli2.text_input("Telefone", key="tel_orc")

        data_orc = c_cli3.date_input("Data", value=date.today(), key="data_orc")

        nome_grupo_pedido = st.text_input("Nome do Produto/Grupo", key="grupo_orc")

        st.write("---")

        c_it1, c_it2 = st.columns([3, 1])

        item_escolhido = c_it1.selectbox("Selecione o Item:", options=[""] + df_ing['nome'].tolist(), key="sel_orc_it")

        qtd_orc = c_it2.number_input("Qtd", min_value=1, value=1, key="q_orc_input")

        st.button("➕ Adicionar Item ao Grupo", use_container_width=True, on_click=adicionar_ao_carrinho)

        

        if st.session_state.carrinho_orc:

            total_venda_bruta_acumulada = 0.0

            total_ingredientes_acumulados = 0.0

            lista_pdf = []

            

            taxa_perc = (taxa_credito_input / 100) if forma_pagamento == "Crédito" else 0.0

            

            for idx, it in enumerate(st.session_state.carrinho_orc):

                c = st.columns([3, 1, 1.5, 1.5, 2, 0.5])

                v_unit_custo_exibicao = it['preco_puro'] * it['qtd']

                total_ingredientes_acumulados += v_unit_custo_exibicao

                

                v_venda_it = (it['preco_puro'] * (1 + (margem_lucro/100))) * it['qtd']

                v_venda_com_taxa_pdf = v_venda_it * (1 + taxa_perc)

                

                total_venda_bruta_acumulada += v_venda_it

                lista_pdf.append({"nome": it['nome'], "qtd": it['qtd'], "venda": v_venda_com_taxa_pdf})

                

                c[0].write(it['nome'])

                c[1].write(f"x{it['qtd']}")

                c[2].write(f"R$ {it['preco_puro']:.2f}")

                c[3].write(f"R$ {v_unit_custo_exibicao:.2f}")

                c[4].write(f"**R$ {v_venda_it:.2f}**")

                if c[5].button("❌", key=f"del_orc_{idx}"):

                    st.session_state.carrinho_orc.pop(idx)

                    st.rerun()

            

            st.divider()

            f1, f2 = st.columns(2)

            frete_val = f1.number_input("Frete Total (R$)", value=0.0, key="frete_orc")

            emb_val = f2.number_input("Embalagem Total (R$)", value=0.0, key="emb_orc")

            

            v_custo_total_orc = total_ingredientes_acumulados + emb_val

            v_lucro_orc = total_venda_bruta_acumulada - v_custo_total_orc

            

            v_subtotal = total_venda_bruta_acumulada + frete_val + emb_val

            v_taxa_cartao_orc = v_subtotal * taxa_perc

            total_geral_orc = v_subtotal + v_taxa_cartao_orc

            

            cmv_perc_orc = (v_custo_total_orc / total_venda_bruta_acumulada * 100) if total_venda_bruta_acumulada > 0 else 0

            cor_cmv_orc = "#4ade80" if cmv_perc_orc <= 35 else "#facc15" if cmv_perc_orc <= 45 else "#f87171"



            res1, res2 = st.columns([1.5, 1])

            with res1:

                st.write("**Detalhamento de Valores (Orçamento)**")

                df_res_orc = pd.DataFrame({

                    "Item": ["Ingredientes", "Embalagem", "Frete", "Taxas Pagamento"],

                    "Valor": [f"R$ {total_ingredientes_acumulados:.2f}", f"R$ {emb_val:.2f}", f"R$ {frete_val:.2f}", f"R$ {v_taxa_cartao_orc:.2f}"]

                })

                st.table(df_res_orc)

            

            with res2:

                st.markdown(f"""

                <div style='background-color: #262730; padding: 20px; border-radius: 10px; border-left: 5px solid #1e3a8a;'>

                    <p style='margin:0; font-size:13px; opacity:0.8; color:white;'>RESUMO DO ORÇAMENTO</p>

                    <p style='margin:0; color:white;'><b>CMV:</b> <span style='color:{cor_cmv_orc}; font-weight:bold;'>{cmv_perc_orc:.1f}%</span></p>

                    <p style='margin:0; color:white;'><b>Lucro Líquido:</b> <span style='color:#4ade80;'>R$ {v_lucro_orc:.2f}</span></p>

                    <hr style='margin:10px 0; border-color:#4b5563;'>

                    <h2 style='margin:0; color:white; font-size:28px;'>R$ {total_geral_orc:.2f}</h2>

                </div>

                """, unsafe_allow_html=True)



            st.write("")

            b_col1, b_col2, b_col3 = st.columns(3)

            pdf_bytes = exportar_pdf(nome_cliente, nome_grupo_pedido, lista_pdf, total_geral_orc)

            b_col1.download_button(label="📄 Gerar Pdf", data=pdf_bytes, file_name=f"Orcamento.pdf", use_container_width=True)

            if b_col2.button("💾 Salvar Orçamento", use_container_width=True):

                df_hist = carregar_historico_orc()

                if df_hist is not None:

                    novo_reg = pd.DataFrame([{"Data": data_orc.strftime("%d/%m/%Y"), "Cliente": nome_cliente, "Pedido": nome_grupo_pedido, "Valor_Final": f"R$ {total_geral_orc:.2f}"}])

                    conn.update(worksheet="Orcamentos_Salvos", data=pd.concat([df_hist, novo_reg], ignore_index=True))

                    st.success("Orçamento salvo!")

            if b_col3.button("🗑️ Limpar Pedido", use_container_width=True):

                st.session_state.carrinho_orc = []

                st.rerun()

    with t2:

        df_salvos = carregar_historico_orc()

        if not df_salvos.empty:

            for i, row in df_salvos.iterrows():

                c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2.5, 1.5, 0.5])

                c1.write(row.get('Data', '')); c2.write(row.get('Cliente', ''))

                c3.write(row.get('Pedido', '')); c4.write(row.get('Valor_Final', ''))

                if c5.button("🗑️", key=f"del_h_{i}"):

                    conn.update(worksheet="Orcamentos_Salvos", data=df_salvos.drop(i)); st.rerun()



def main():

    df_ing = carregar_ingredientes()

    df_rec = carregar_receitas_nuvem()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador</h1>", unsafe_allow_html=True)



    with st.sidebar:

        st.header("⚙️ Ajuste de Taxas")

        # TAXA FIXA EM 6%

        taxa_credito_input = 6.0

        st.write(f"Taxa Crédito Fixa: {taxa_credito_input}%")

        st.divider()

        km_gratis = st.number_input("KM Isentos", value=5)

        valor_por_km = st.number_input("R$ por KM adicional", value=2.0, step=0.1)



    with st.expander("📂 Abrir ou Deletar Receitas Salvas"):

        receitas_nomes = df_rec['nome_receita'].unique().tolist() if not df_rec.empty else []

        col_rec1, col_rec2, col_rec3 = st.columns([2, 1, 1])

        with col_rec1:

            receita_selecionada = st.selectbox("Selecione uma receita:", [""] + receitas_nomes)

        with col_rec2:

            st.write("") 

            if st.button("🔄 Carregar", use_container_width=True) and receita_selecionada != "":

                dados_rec = df_rec[df_rec['nome_receita'] == receita_selecionada]

                st.session_state.nome_prod_input = receita_selecionada

                st.session_state.n_itens_receita = len(dados_rec)

                st.session_state.versao_lista += 1 

                for idx, row in enumerate(dados_rec.itertuples()):

                    st.session_state[f"nome_{idx}"] = row.ingrediente

                    st.session_state[f"qtd_{idx}"] = float(row.qtd)

                    st.session_state[f"u_{idx}"] = row.unid

                st.rerun()

        with col_rec3:

            st.write("")

            if st.button("🗑️ Deletar", use_container_width=True) and receita_selecionada != "":

                df_restante = df_rec[df_rec['nome_receita'] != receita_selecionada]

                conn.update(worksheet="Receitas", data=df_restante)

                st.warning(f"Receita '{receita_selecionada}' removida!")

                st.rerun()



    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])

    with col_p1:

        nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_prod_input")

    with col_p2:

        margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=135)

    with col_p3:

        distancia_km = st.number_input("Distância (km)", min_value=0.0, value=0.0, step=0.1)

    with col_p4:

        forma_pagamento = st.selectbox("Pagamento", ["Crédito", "PIX"])

        

    st.divider()



    custo_ingredientes_total = 0.0

    col_esq, col_dir = st.columns([2, 1])

    with col_esq:

        st.subheader("🛒 Ingredientes")

        n_itens = st.number_input("Número de itens:", min_value=1, value=st.session_state.n_itens_receita, key=f"n_itens_widget_{st.session_state.versao_lista}")

        st.session_state.n_itens_receita = n_itens 

        

        lista_para_salvar = []

        if not df_ing.empty:

            for i in range(st.session_state.n_itens_receita):

                c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1.5, 0.5])

                with c1:

                    lista_nomes = df_ing['nome'].tolist()

                    val_nome = st.session_state.get(f"nome_{i}")

                    idx_nome = lista_nomes.index(val_nome) if val_nome in lista_nomes else 0

                    escolha = st.selectbox(f"Item {i+1}", options=lista_nomes, index=idx_nome, key=f"nome_{i}_{st.session_state.versao_lista}")

                    st.session_state[f"nome_{i}"] = escolha

                

                dados_item = df_ing[df_ing['nome'] == escolha].iloc[0]

                with c2:

                    val_qtd = st.session_state.get(f"qtd_{i}", 0.0)

                    qtd_usada = st.number_input(f"Qtd", value=val_qtd, key=f"qtd_{i}_{st.session_state.versao_lista}", step=0.01)

                    st.session_state[f"qtd_{i}"] = qtd_usada

                with c3:

                    unid_opcoes = ["g", "kg", "ml", "L", "unidade"]

                    val_unid = st.session_state.get(f"u_{i}")

                    idx_unid = unid_opcoes.index(val_unid) if val_unid in unid_opcoes else 0

                    unid_uso = st.selectbox(f"Unid", options=unid_opcoes, index=idx_unid, key=f"u_{i}_{st.session_state.versao_lista}")

                    st.session_state[f"u_{i}"] = unid_uso

                

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

                with c5:

                    st.write("")

                    if st.button("❌", key=f"del_ing_man_{i}"):

                        for j in range(i, st.session_state.n_itens_receita - 1):

                            st.session_state[f"nome_{j}"] = st.session_state.get(f"nome_{j+1}")

                            st.session_state[f"qtd_{j}"] = st.session_state.get(f"qtd_{j+1}")

                            st.session_state[f"u_{j}"] = st.session_state.get(f"u_{j+1}")

                        st.session_state.n_itens_receita -= 1

                        st.session_state.versao_lista += 1 

                        st.rerun()



    with col_dir:

        st.subheader("⚙️ Adicionais")

        perc_quebra = st.slider("Quebra (%)", 0, 15, 2)

        perc_despesas = st.slider("Despesas Gerais (%)", 0, 100, 30)

        valor_embalagem_manual = st.number_input("Embalagem (R$)", min_value=0.0, value=0.0, key="emb_manual")



    taxa_entrega = (distancia_km - km_gratis) * valor_por_km if distancia_km > km_gratis else 0.0

    v_quebra = custo_ingredientes_total * (perc_quebra / 100)

    v_despesas = custo_ingredientes_total * (perc_despesas / 100)

    v_cmv = custo_ingredientes_total + v_quebra + valor_embalagem_manual

    custo_total_prod = v_cmv + v_despesas

    lucro_valor = custo_total_prod * (margem_lucro / 100)

    preco_venda_produto = custo_total_prod + lucro_valor

    t_percentual = (taxa_credito_input / 100) if forma_pagamento == "Crédito" else 0.0

    v_taxa_financeira = (preco_venda_produto + taxa_entrega) * t_percentual

    preco_venda_final = preco_venda_produto + taxa_entrega + v_taxa_financeira

    cmv_percentual = (v_cmv / preco_venda_produto * 100) if preco_venda_produto > 0 else 0

    cor_cmv = "#4ade80" if cmv_percentual <= 35 else "#facc15" if cmv_percentual <= 45 else "#f87171"



    st.divider()

    res1, res2 = st.columns([1.5, 1])

    with res1:

        st.markdown(f"### Detalhamento: {nome_produto_final if nome_produto_final else 'Novo Produto'}")

        df_resumo = pd.DataFrame({

            "Item": ["Ingredientes", "Quebra", "Despesas Gerais", "Embalagem", "Custo Produção", "CMV (%)", "Lucro", "Entrega", "Taxas", "TOTAL FINAL"],

            "Valor": [f"R$ {custo_ingredientes_total:.2f}", f"R$ {v_quebra:.2f}", f"R$ {v_despesas:.2f}", f"R$ {valor_embalagem_manual:.2f}", f"R$ {custo_total_prod:.2f}", f"{cmv_percentual:.1f}%", f"R$ {lucro_valor:.2f}", f"R$ {taxa_entrega:.2f}", f"R$ {v_taxa_financeira:.2f}", f"R$ {preco_venda_final:.2f}"]

        })

        st.table(df_resumo)

        if st.button("💾 Salvar Receita", use_container_width=True):

            if nome_produto_final:

                df_nova = pd.DataFrame(lista_para_salvar)

                if df_rec is not None:

                    df_final = pd.concat([df_rec[df_rec['nome_receita'] != nome_produto_final], df_nova], ignore_index=True)

                    conn.update(worksheet="Receitas", data=df_final)

                    st.success(f"Receita '{nome_produto_final}' salva!")

                    st.rerun()



    with res2:

        st.markdown(f"<div class='resultado-box'><p style='margin:0; font-size:14px; opacity: 0.8;'>VALOR SUGERIDO</p><h2 style='margin:0;'>TOTAL ({forma_pagamento})</h2><h1 style='color: #60a5fa !important; font-size:48px;'>R$ {preco_venda_final:.2f}</h1><hr style='border-color: #4b5563;'><p><b>Lucro Líquido:</b> <span style='color: #4ade80;'>R$ {lucro_valor:.2f}</span></p><p><b>CMV:</b> <span style='color: {cor_cmv}; font-weight: bold;'>{cmv_percentual:.1f}%</span></p><p>Custo Produção: R$ {custo_total_prod:.2f}</p></div>", unsafe_allow_html=True)



    secao_orcamento(df_ing, margem_lucro, taxa_credito_input, forma_pagamento)



if __name__ == "__main__":

    main()
