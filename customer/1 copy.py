def assistant_node(state: State, config: RunnableConfig):
    """
    Consolidated Assistant Node: HR Support, Data Analytics, and Customer Concierge.
    Handles multiple roles and tool calling.
    """
    tenant_id = config["configurable"].get("tenant_id", "unknown")
    conversation_id = config["configurable"].get("thread_id", "unknown")
    messages = state["messages"]
    logger.info(f"Messages before assistant processing: {messages}")
    log_info(f"Assistant node triggered for tenant: {tenant_id} with nessage : {messages}", tenant_id, conversation_id)

    # --- Resolve DB-sourced prompts with hardcoded fallbacks ---
    tenant_config = state.get("tenant_config") or {}
    # employee_id = {state.get('employee_id')}
    employee_id = str(state.get('employee_id', 'unknown'))
    current_year = datetime.now().year
    previous_year = current_year - 1
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    status_summary = state.get("status_summary", "No active application.")
    pdf_content = state.get("pdf_content", "None")
    web_content = state.get("web_content", "None")
    sql_result = state.get("sql_result", "None")
    tool_intent_map = ((state.get("tenant_config") or {}).get("tool_intent_map")
  or tool_guide
   )
    # global_answer_prompt acts as the persona/intro section of system_prompt.
    # Falls back to GLOBAL_FINAL_ANSWER_PROMPT if not set in the DB.
    global_answer_prompt = (
        tenant_config.get("global_answer_prompt1")
        or GLOBAL_FINAL_ANSWER_PROMPT
    )
    
    # agent_prompt is the full system prompt stored in DB (used as an alternative
    # intro when set). If absent, the composed prompt below is used instead.
    # agent_prompt = tenant_config.get("agent_prompt") or None

    # Fetch the prompt template
    agent_prompt = tenant_config.get("agent_prompt1",GLOBAL_FINAL_ANSWER_PROMPT)

    # Build string of tool descriptions and arguments
    tool_descriptions = "\n".join([f"- {t.name}: {t.description}\n  Arguments schema: {t.args}" for t in tools])

    if agent_prompt:
        try:
            
         system_prompt = agent_prompt.format(
            ID=employee_id,
            current_year=current_year,
            previous_year=previous_year,
            current_date_str=current_date_str,
            pdf_content=pdf_content,
            web_content=web_content,
            # Using leave_application for the state result as requested
            sql_result=sql_result,
            status_summary=status_summary,
            tool_intent_map=tool_intent_map,
            tool_descriptions=tool_descriptions
        )
        except KeyError as e:
            logger.error(f"Missing key in prompt template: {e}")
            system_prompt = agent_prompt # Fallback to raw if format fails
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

   

    # 3. LLM INVOCATION
 
    # Check if last message was a tool result (we might already be done)
    if messages and isinstance(messages[-1], ToolMessage):
        logger.info("Last message was a tool result. LLM will now generate the final JSON response based on the tool's output.")

    # logger.info(f"!!! TRACE: assistant_node starting. Messages: {len(messages)}", flush=True)

    logger.info(f"!!! TRACE: assistant_node starting. Messages: {len(messages)}")
    try:
        # 1. Capture the raw response WITH bind_tools
        # Use the global 'llm' instance directly to avoid redundant/unstable DB calls inside the graph
        logger.info(f"Messages before assistant processing: {messages}")
        llm = get_model() 
        logger.info(f"LLM instance: {llm}", tenant_id, conversation_id)
        if not llm:
            logger.error("LLM instance is not available. Returning error response.", tenant_id, conversation_id)
            return {"messages": [AIMessage(content=json.dumps({"tool": "none", "answer": "Error: LLM not available."}))]}
        logger.info(f"Tools: {tools}", tenant_id, conversation_id)
        llm_with_tools = llm.bind_tools(tools)
        logger.info(f"LLM with tools: {llm_with_tools}", tenant_id, conversation_id)
        safe_messages = clean_message_history(state["messages"])
        logger.info(f"Safe messages: {safe_messages}", tenant_id, conversation_id)
        try:
            response = llm_with_tools.invoke([SystemMessage(content=system_prompt)] + safe_messages)
            logger.info(f"LLM Raw Output: {response}", tenant_id, conversation_id)
        except Exception as e:
            log_error(f"LLM invoke failed: {e}", tenant_id, conversation_id)
            return {"messages": [AIMessage(content=json.dumps({"answer": "I'm sorry, I'm experiencing connectivity issues. Please try again later."}))]}
        
        logger.info(f"LLM Raw Output: {response}", tenant_id, conversation_id)
    except BaseException as e:
        import traceback
        logger.error(f"CRITICAL CRASH in assistant_node: {e}\n{traceback.format_exc()}", tenant_id, conversation_id)
        raise e
    refined_response = normalize_tool_calls(response)
    if refined_response.tool_calls:
        logger.info(f"Tool call detected: {refined_response.tool_calls}")
        return {"messages": [refined_response]}
    else:
        # Handle as standard text response
        final_answer = extract_final_answer(refined_response)
        logger.info(f"LLM response Assitant Node: {final_answer}")
        return {"messages": [AIMessage(content=final_answer)]}
    
    # if hasattr(refined_response, "tool_calls") and refined_response.tool_calls:
    #             logger.info(f"Tool calls foundAtejjd: {refined_response.tool_calls}")
    #             return {"messages": [refined_response]}  # keep the AIMessage intact

    # else:
    #     extract_final_answer(refined_response) and (not hasattr(refined_response, "tool_calls") or not refined_response.tool_calls):
    #         # Attach chart if present in state
    #     viz_result = state.get("visualization_result")
    #     if viz_result and "image_base64" in viz_result:
    #             refined_response.chart_base64 = viz_result["image_base64"]
                
    #         return {
    #             "messages": [AIMessage(content=refined_response.content)],
    #             "status_summary": status_summary
    #         }   
