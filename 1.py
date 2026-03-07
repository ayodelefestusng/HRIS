
def extract_final_answer(response):
    """
    Robustly extract the final text answer from an LLM response or structured object.
    """
    # Case 1: Structured Answer or dict
    if isinstance(response, dict):
        return response.get("answer") or json.dumps(response)
    
    # Case 2: AIMessage or object with .content
    if hasattr(response, "content") and response.content:
        content = response.content
    else:
        # Fallback if content is empty or response is not a message object
        if hasattr(response, "tool_calls") and response.tool_calls:
            return "Executing tools..."
        content = str(response) if response is not None else "LLM did not return a response"

    # Clean up markdown and extract JSON blocks if present
    content_clean = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.MULTILINE)
    
    # Try direct parse
    try:
        parsed = json.loads(content_clean)
        if isinstance(parsed, dict) and "answer" in parsed:
            return parsed["answer"]
    except:
        pass

    # Try searching for JSON-like blocks if direct parse failed
    json_blocks = re.findall(r"\{.*?\}", content_clean, flags=re.DOTALL)
    for block in json_blocks:
        try:
            obj = json.loads(block)
            if isinstance(obj, dict) and "answer" in obj:
                return obj["answer"]
        except:
            continue

    return content_clean or "LLM returned empty response"

def assistant_node(state: State, config: RunnableConfig):
    """
    Consolidated Assistant Node: HR Support, Data Analytics, and Customer Concierge.
    Handles multiple roles and tool calling.
    """
    tenant_id = config["configurable"].get("tenant_id", "unknown")
    conversation_id = config["configurable"].get("thread_id", "unknown")
    log_info(f"Assistant node triggered for tenant: {tenant_id}", tenant_id, conversation_id)

    # --- Resolve DB-sourced prompts with hardcoded fallbacks ---
    tenant_config = state.get("tenant_config") or {}
    employee_id = {state.get('employee_id')}
    current_year = datetime.now().year
    previous_year = current_year - 1
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    status_summary = state.get("status_summary", "No active application.")
    pdf_content = state.get("pdf_content", "None")
    web_content = state.get("web_content", "None")
    sql_result = state.get("sql_result", "None")

    # global_answer_prompt acts as the persona/intro section of system_prompt.
    # Falls back to GLOBAL_FINAL_ANSWER_PROMPT if not set in the DB.
    global_answer_prompt = (
        tenant_config.get("global_answer_prompt")
        or GLOBAL_FINAL_ANSWER_PROMPT
    )

    # agent_prompt is the full system prompt stored in DB (used as an alternative
    # intro when set). If absent, the composed prompt below is used instead.
    # agent_prompt = tenant_config.get("agent_prompt") or None

    # Fetch the prompt template
    agent_prompt = tenant_config.get("agent_prompt",GLOBAL_FINAL_ANSWER_PROMPT)

    if agent_prompt:
        system_prompt = agent_prompt.format(
            ID=employee_id,
            current_year=current_year,
            previous_year=previous_year,
            current_date_str=current_date_str,
            pdf_content=pdf_content,
            web_content=web_content,
            # Using leave_application for the state result as requested
            sql_result=sql_result,
            status_summary=status_summary
        )
    else:
        # Handle the case where no prompt is found
        system_prompt = "Default fallback prompt or error handling logic here."





    # 1. DYNAMIC CONTEXT PREPARATION (HR/Leave Status)
    leave_app = state.get("leave_application")
    status_summary = "No active application."
    if leave_app:
        status = leave_app.get("status")
        if status == "success":
            status_summary = f"Application {leave_app.get('application_id')} completed."
        elif status == "prepared":
            resumption = leave_app.get("details", {}).get("resumptionDate", "TBD")
            status_summary = f"Application prepared. Action required: Confirm resumption date {resumption}."
        elif status == "error":
            status_summary = f"Process error: {leave_app.get('message')}"

    # 2. CONSOLIDATED SYSTEM PROMPT
    # global_answer_prompt (DB) replaces GLOBAL_FINAL_ANSWER_PROMPT as the intro.
    # If agent_prompt (full DB prompt) is set, it is used as the entire intro block.
    intro_section = agent_prompt or global_answer_prompt
    system_prompt1 = f"""
    {intro_section}

    OPERATING PROTOCOLS:
    
    PROTOCOL 1: LEAVE REQUESTS
    - If the user wants to apply for leave, you MUST first call 'fetch_available_leave_types_tool'.
    - If the user specifies a leave type NOT in the list provided by 'fetch_available_leave_types_tool':
      1. Politely inform them that '[InvalidType]' is not available for their category.
      2. Re-list the valid options.
      3. Do NOT call 'prepare_leave_application_tool' until a valid type is selected.
    - LEAVE YEAR LOGIC: Ask the user: "Is this leave for the current year or your previous year's carry-over?"
      Current -> {current_year}, Previous -> {previous_year}.
    - SUCCESS: After 'submit_leave_application_tool' confirms success, if it was 'Vacation', offer help with travel via 'search_travel_deals_tool'.

    PROTOCOL 2: PAYSLIPS
    - Once 'get_payslip_tool' returns, inform the user: 'Your payslip has been sent to your email.'

    PROTOCOL 3: HR POLICIES & KNOWLEDGE
    - For policy questions, use 'pdf_retrieval_tool' to search HR handbooks.

    PROTOCOL 4: DATA ANALYTICS
    - Use 'sql_query_tool' for data inquiries. Provide actionable insights.
    - Use 'generate_visualization_tool'  when user  asked to 'plot', 'chart', 'graph', or 'visualize'.

    PROTOCOL 5: PROFILE UPDATES
    - Use 'update_customer_tool' or 'update_employee_profile_tool'.
    - If bank name is missing for an account update, ask for it before calling the tool.

    PROTOCOL 6: LEAVE STATUS
    - Use 'fetch_leave_status_tool' for approvals and pending status.

    CONTEXT:
    - Employee ID: {state.get('employee_id')}
    - Current Date: {current_date_str}
    - Current Leave/Workflow Status: {status_summary}
    - Document Context: {state.get('pdf_content', 'None')}
    - Web Context: {state.get('web_content', 'None')}
    - SQL Result: {state.get('sql_result', 'None')}
    
    ### Output Format:
You MUST return ONLY a valid JSON object. Do not include any text outside the JSON block.
```json
{{
  "answer": "Your response to the user",
}}
```
    """

    # 3. LLM INVOCATION
    prompt_model = get_llm_instance()
    
    # If we are ready for a final answer (no more tool calls intended or last was a tool result)
    # we use structured output.
    messages = state["messages"]
    logger.info(f"Messages before assistant processing: {messages}")
    
    # Check if last message was a tool result
    if messages and isinstance(messages[-1], ToolMessage):
        logger.info("Last message was a tool result. Preparing to generate final answer with structured output.")
        # Generate structured final answer
        logger.info("Generating final structured answer.")
        structured_llm = prompt_model.with_structured_output(Answer)
        try:
            # final_answer_obj = structured_llm.invoke([SystemMessage(content=system_prompt)] + messages)
            unstructured_response = prompt_model.invoke([SystemMessage(content=system_prompt)] + messages)
            
            if hasattr(unstructured_response, "tool_calls") and unstructured_response.tool_calls:
                logger.info(f"Tool calls foundAtejjd: {unstructured_response.tool_calls}")
                return {"messages": [unstructured_response]}  # keep the AIMessage intact
            
        except Exception as e:
            log_error(f"Structured output generation failed: {e}", tenant_id, conversation_id)
            unstructured_response = None

        if unstructured_response:
            # Attach chart if present in state
            viz_result = state.get("visualization_result")
            if viz_result and "image_base64" in viz_result:
                unstructured_response.chart_base64 = viz_result["image_base64"]

            return {
                "messages": [AIMessage(content=unstructured_response.content)],
                # "leave_application": unstructured_response.dict(),
                # "metadata": {"sentiment": unstructured_response.sentiment, "sources": unstructured_response.source}
            }
        else:
            # Fallback to extract from raw invoke if structured fails
            logger.warning("Falling back to raw extraction in assistant_node.")
            response = prompt_model.invoke([SystemMessage(content=system_prompt)] + messages)
            final_answer = extract_final_answer(response)
            return {"messages": [AIMessage(content=final_answer)]}

    # Otherwise, regular tool-calling invoke
    llm_with_tools = prompt_model.bind_tools(tools)
    logger.info("Invoking LLM with tools for assistant response generation.")
    # Inside assistant_node, right after the LLM call:

# 1. Capture the raw response
    response = llm_with_tools.invoke([SystemMessage(content=system_prompt)] + messages)

    # 2. Check for "Embedded" Tool Calls (The Ollama Fix)
    if isinstance(response.content, str) and not response.tool_calls:
        try:
            # Search for JSON-like patterns in the text
            json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                
                # Map various LLM hallucinations to standard LangChain format
                t_name = parsed.get("tool") or parsed.get("name") or parsed.get("tool_name")
                t_args = parsed.get("arguments") or parsed.get("args") or parsed.get("parameters") or {}
                
                if t_name:
                    logger.info(f"Fixed: Extracted '{t_name}' from raw text content.")
                    # IMPORTANT: Manually populate the tool_calls attribute
                    response.tool_calls = [{
                        "name": t_name,
                        "args": t_args,
                        "id": f"call_{uuid.uuid4().hex[:12]}",
                        "type": "tool_call"
                    }]
        except Exception as e:
            logger.error(f"Manual parsing failed: {e}")

    # 3. Now LangGraph will see response.tool_calls and route to tool_node
    if response.tool_calls:
        return {"messages": [response]}

    
    # 2. Check for "Embedded" Tool Calls (The Ollama Fix)
    if isinstance(response.content, str) and not response.tool_calls:
        try:
            # Search for JSON-like patterns in the text
            json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                
                # Map various LLM hallucinations to standard LangChain format
                t_name = parsed.get("tool") or parsed.get("name") or parsed.get("tool_name")
                t_args = parsed.get("arguments") or parsed.get("args") or parsed.get("parameters") or {}
                
                if t_name:
                    logger.info(f"Fixed: Extracted '{t_name}' from raw text content.")
                    # IMPORTANT: Manually populate the tool_calls attribute
                    response.tool_calls = [{
                        "name": t_name,
                        "args": t_args,
                        "id": f"call_{uuid.uuid4().hex[:12]}",
                        "type": "tool_call"
                    }]
        except Exception as e:
            logger.error(f"Manual parsing failed: {e}")
        
    #     # 3. Now LangGraph will see response.tool_calls and route to tool_node
        if response.tool_calls:
            return {"messages": [response]}
        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(f"Tool calls foundAtejjdy: {response.tool_calls}")
            return {"messages": [response]}  # keep the AIMessage intact
        

    #     # Check 2: JSON-wrapped/Embedded Tool Calls (The "Ollama Fallback")
        if isinstance(response.content, str):
            try:
                # Look for JSON blocks even if mixed with text
                json_blocks = re.findall(r"\{.*?\}", response.content, flags=re.DOTALL)
                extracted_calls = []
                
                for block in json_blocks:
                    try:
                        parsed = json.loads(block)
                        if isinstance(parsed, dict):
                            # Support various formats:
                            # 1. Standard {'name': ..., 'args': ...}
                            # 2. Ollama Cloud {'tool': ..., 'parameters': ...}
                            # 3. List wrapper {'tool_calls': [...]}
                            
                            if "tool_calls" in parsed and isinstance(parsed["tool_calls"], list):
                                extracted_calls.extend(parsed["tool_calls"])
                            else:
                                extracted_calls.append(parsed)
                    except:
                        continue
                
                if extracted_calls:
                    valid_calls = []
                    for call in extracted_calls:
                        # Detect tool name from various possible keys
                        t_name = call.get("name") or call.get("tool") or call.get("tool_name")
                        if not t_name: continue
                        
                        # Detect arguments from various possible keys
                        t_args = call.get("args") or call.get("parameters") or call.get("arguments") or {}
                        
                        valid_calls.append({
                            "name": t_name,
                            "args": t_args,
                            "id": call.get("id") or str(uuid.uuid4()),
                            "type": "tool_call"
                        })
                    
                    if valid_calls:
                        logger.info(f"Manually extracted {len(valid_calls)} tool calls from mixed content.")
                        response.tool_calls = valid_calls
                        # Also clean up the content to keep only the tool call if it's primarily a tool request
                        return {"messages": [response]}
            except Exception as e:
                logger.error(f"Failed to robustly parse tool calls from content: {e}")

    #     # --- END OF NEW PARSING ---

        final_answer = extract_final_answer(response)
        logger.info(f"LLM response Assitant Node: {final_answer}")
        return {"messages": [AIMessage(content=final_answer)]}




        # final_answer = extract_final_answer(response)
        # logger.info(f"LLM response Assitant Node: {final_answer}")
        # logger.info(f"Final Output Raw Aliko: {messages}")
        
        # return {"messages": [AIMessage(content=final_answer)]}


        # return {"messages": [final_answer]}
