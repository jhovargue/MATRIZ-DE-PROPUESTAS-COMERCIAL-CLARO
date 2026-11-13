def extract_receipt_data(file_bytes, filename, recommend_mode, modality_choice="PDV"):
    extracted_lines = []
    full_text = ""
    is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg'))
    operator_hotlines = ["966000000", "900000000", "999999999"]
    processed_phones = set()

    # Operadores para omitir sus RUCs
    operator_rucs = ["20100017491", "20414955020", "20504771424", "20263322496", "20106897914"]

    if not is_image:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                # 1. Buscar en todas las páginas la tabla oficial de Resumen de Entel
                for page in pdf.pages:
                    p_text = page.extract_text() or ""
                    full_text += p_text + "\n"

                    tables = page.extract_tables()
                    for tbl in tables:
                        for row in tbl:
                            if not row or len(row) < 5:
                                continue
                            
                            row_str_cells = [str(c).strip() if c is not None else "" for c in row]
                            joined_row = " ".join(row_str_cells)

                            # Buscar número celular de 9 dígitos que comience con 9
                            phone_match = re.search(r"\b(9\d{8})\b", joined_row)
                            if not phone_match:
                                continue

                            ph = phone_match.group(1)
                            if ph in processed_phones or ph in operator_hotlines or ph in st.session_state.deleted_phones:
                                continue

                            # Detectar nombre del plan tarifario (ej. "Empresa PRO 2.0 44.9")
                            plan_match = re.search(r"(Empresa\s+PRO[^\d]*\d+(?:\.\d+)?|Empresa\s+[A-Za-z0-9\.\s]+)", joined_row, re.IGNORECASE)
                            if plan_match:
                                plan_name = plan_match.group(1).strip()
                                # Limpiar posibles residuos numéricos de columnas contiguas
                                plan_name = re.sub(r"\s+", " ", plan_name)
                            else:
                                plan_name = "Empresa PRO"

                            # Extraer todos los valores numéricos monetarios de la fila
                            amounts = re.findall(r"[-+]?\b\d+\.\d{2}\b", joined_row)
                            if len(amounts) >= 3:
                                # Estructura Entel Resumen: [Plan(CF), Prorrateo, Adicionales, Descuentos, ..., Monto Final]
                                cf = float(amounts[0])
                                negatives = [abs(float(a)) for a in amounts if float(a) < 0]
                                disc_val = negatives[0] if negatives else 0.0
                                pay = float(amounts[-1])
                            else:
                                cf = 44.90
                                disc_val = 0.0
                                pay = cf

                            # Validar Descuento
                            if disc_val > 0 and cf > 0:
                                discount_pct = round((disc_val / cf) * 100, 0)
                            else:
                                discount_pct = 0.0

                            # Si el nombre del plan no traía el valor explícito, concatenarlo
                            if not re.search(r"\d", plan_name):
                                plan_name = f"{plan_name} {cf:.1f}"

                            rec = recommend_plan_movil(cf, recommend_mode, modality_choice)
                            extracted_lines.append({
                                "id": str(pd.Timestamp.now().timestamp()) + "_" + ph,
                                "phone": ph,
                                "operator": "Entel",
                                "plan": plan_name,
                                "cf": cf,
                                "discount": discount_pct,
                                "pay": pay,
                                "claro_plan_idx": DEFAULT_PLANS_MOVIL.index(rec),
                                "source": filename,
                            })
                            processed_phones.add(ph)

                # 2. Si no encontró tablas estructuradas (fallback a parsing línea por línea)
                if not extracted_lines:
                    for line in full_text.split("\n"):
                        line_str = line.strip()
                        m_phone = re.search(r"\b(9\d{8})\b", line_str)
                        if m_phone:
                            ph = m_phone.group(1)
                            if ph in processed_phones or ph in operator_hotlines or ph in st.session_state.deleted_phones:
                                continue

                            amounts = re.findall(r"[-+]?\b\d+\.\d{2}\b", line_str)
                            if len(amounts) >= 3:
                                cf = float(amounts[0])
                                negatives = [abs(float(a)) for a in amounts if float(a) < 0]
                                disc_val = negatives[0] if negatives else 0.0
                                pay = float(amounts[-1])
                            else:
                                cf = 44.90
                                disc_val = 0.0
                                pay = cf

                            discount_pct = round((disc_val / cf) * 100, 0) if (cf > 0 and disc_val > 0) else 0.0

                            plan_match = re.search(rf"{ph}\s+(.+?)\s+{amounts[0]}" if amounts else rf"{ph}\s+(.+)", line_str)
                            plan_name = plan_match.group(1).strip() if plan_match else f"Empresa PRO 2.0 {cf:.1f}"

                            rec = recommend_plan_movil(cf, recommend_mode, modality_choice)
                            extracted_lines.append({
                                "id": str(pd.Timestamp.now().timestamp()) + "_" + ph,
                                "phone": ph,
                                "operator": "Entel" if "entel" in full_text.lower() else "Movistar",
                                "plan": plan_name,
                                "cf": cf,
                                "discount": discount_pct,
                                "pay": pay,
                                "claro_plan_idx": DEFAULT_PLANS_MOVIL.index(rec),
                                "source": filename,
                            })
                            processed_phones.add(ph)

        except Exception as e:
            st.error(f"Error procesando PDF: {e}")
            return []

    # Detección de RUC y Razón Social de la empresa
    ruc_encontrado = None
    all_rucs = re.findall(r"\b([12]\d{10})\b", full_text)
    for r in all_rucs:
        if r not in operator_rucs:
            ruc_encontrado = r
            break
    if ruc_encontrado:
        st.session_state.ruc = ruc_encontrado
        st.session_state["ruc_input_movil_val"] = ruc_encontrado
        st.session_state["ruc_input_fija"] = ruc_encontrado
        st.session_state["ruc_input_equipos"] = ruc_encontrado

    suffixes = [r"S\.?A\.?C\.?", r"E\.?I\.?R\.?L\.?", r"S\.?A\.?", r"S\.?R\.?L\.?"]
    for line in full_text.split("\n"):
        if any(re.search(rf"\b{s}\b", line, re.IGNORECASE) for s in suffixes):
            if not any(k in line.upper() for k in ["ENTEL", "TELEFONICA", "MOVISTAR", "CLARO"]):
                clean_name = re.sub(r"^(?:Señor\(es\)|Cliente|Razón Social)[\s:]*", "", line, flags=re.IGNORECASE).strip()
                clean_name = re.sub(r"(?:RUC|N[º°]|Doc|Dirección).*", "", clean_name, flags=re.IGNORECASE).strip()
                if len(clean_name) >= 4:
                    st.session_state.company = clean_name
                    st.session_state["company_input_movil_val"] = clean_name
                    break

    return extracted_lines