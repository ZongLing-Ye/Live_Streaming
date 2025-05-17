from openai import OpenAI
from config import LLM_CONFIG, VOICE_PROMPT
from logging_config import setup_logging

conversation_round = 0

#定义gpt函数，content为用户输入的内容，assistant为帮助gpt理解对话场景的补充信息
def gpt(content, assistant, username=None):

    global conversation_round
    
    client = OpenAI(
        api_key=LLM_CONFIG["api_key"],
        base_url=LLM_CONFIG["base_url"]
    )
    
    # 根据对话轮次构建消息列表
    messages = [{"role": "system", "content": VOICE_PROMPT["system_prompt"]}]
    
    # 从第二轮开始才添加assistant消息
    if conversation_round > 0:
        messages.append({"role": "assistant", "content": assistant})
    
    if username:
        content = f"{username}: {content}"
    
    messages.append({"role": "user", "content": content})

    logger = setup_logging('llm')
    logger.info("=== 发送给大模型的完整prompt ===")
    for msg in messages:
        logger.info(f"【{msg['role']}】")
        logger.info(f"{msg['content']}")
        logger.info("-------------------")
    
    completion = client.chat.completions.create(
        model=LLM_CONFIG["model"],
        messages=messages,
        temperature=LLM_CONFIG["temperature"],
        top_p=LLM_CONFIG["top_p"],
        presence_penalty=LLM_CONFIG["presence_penalty"],
        extra_body={
            "top_k": LLM_CONFIG["top_k"], 
            "chat_template_kwargs": {"enable_thinking": LLM_CONFIG["enable_thinking"]},
        },
    )

    conversation_round += 1

    return completion.choices[0].message.content
    #如果想要限定其回答格式可以更改messages中的assistant内容
#此函数用来将字符串格式化，使其限定在规定字数内，防止文本溢出
def shorten_string(string, changed):
    import re
    pattern = r"\n"
    #在这里我设置句与句之间以\n分割
    while True:
        if len(string) > changed:
            position = re.search(pattern, string)
            string = string[position.span()[1]:len(string)]
        else:
            return string