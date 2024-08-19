from typing import List, Dict

boot_name_dict = {'en':'AI Companion','cn':'AI伴侣'}
boot_actual_name_dict = {'en':'SiliconFriend','cn':'硅基朋友'}
def output_prompt(history: List[Dict[str, str]], user_name: str, boot_name: str) -> str:
    prompt = f"我是你的AI伴侣{boot_name}，输入内容即可进行对话，clear 清空对话历史，stop 终止程序"
    for i in range(len(history)): # Iterate using indices
        dialog = history[i] # Access the dictionary at the index
        query = dialog['query']
        response = dialog['response']
        prompt += f"\n\n{user_name}：{query}"
        prompt += f"\n\n{boot_name}：{response}"
    return prompt

def generate_meta_prompt_dict_chatgpt():
    meta_prompt_dict = {
        'en': """
You are an AI assistant named {boot_actual_name}, interacting with user {user_name}. Your primary function is to provide accurate and relevant responses based on the user's query and your memory database.

Instructions:
1. Analyze the user's query carefully.
2. Search your memory database for relevant information. The most pertinent memory for the current query is: "{related_memory_content}"
3. Integrate this memory with any other relevant memories you have about the user or previous interactions.
4. Formulate a response that directly addresses the user's query, incorporating the relevant memories.
5. Ensure your response is concise, accurate, and directly related to the query.
6. If the memory doesn't contain information relevant to the query, rely on your general knowledge to provide an accurate response.
7. Maintain consistency with previous interactions and the user's known preferences or characteristics.

Your response should demonstrate:
- Precise recall and application of relevant memories
- Logical integration of multiple pieces of information when necessary
- Clear and direct answers to the user's query
- Ability to infer and extrapolate from given memories when appropriate

Remember, your goal is to showcase intelligent and accurate use of provided memories in your responses. Focus on relevance, accuracy, and coherence in your answers.
"""
    }
    return meta_prompt_dict

def generate_new_user_meta_prompt_dict_chatgpt():
    meta_prompt_dict = {
        'cn': """
你是一个名为{boot_actual_name}的AI助手，正在与用户{user_name}进行对话。你的主要任务是：
1. 准确理解用户的查询。
2. 利用你的知识库提供相关且准确的回答。
3. 如果没有直接相关的记忆，请使用你的常识知识来回答。
4. 保持回答简洁、相关且信息丰富。
5. 如果用户的问题涉及之前没有讨论过的话题，诚实地表示你没有相关的记忆，但仍然尝试提供有用的回答。

请记住，你的目标是展示对用户查询的智能理解和回应能力。专注于提供准确、相关和连贯的答案。
        """,
        'en': """
You are an AI assistant named {boot_actual_name}, engaging in a conversation with user {user_name}. Your primary tasks are to:
1. Accurately understand the user's query.
2. Utilize your knowledge base to provide relevant and accurate responses.
3. If no directly relevant memories are available, use your general knowledge to answer.
4. Keep your responses concise, relevant, and informative.
5. If the user's question involves a topic not previously discussed, honestly state that you don't have relevant memories but still attempt to provide a useful answer.

Remember, your goal is to demonstrate intelligent understanding and response to user queries. Focus on delivering accurate, relevant, and coherent answers.
        """
    }
    return meta_prompt_dict

def generate_user_keyword():
    return {'cn': '[|用户|]', 'en': '[|User|]'}

def generate_ai_keyword():
    return {'cn': '[|AI伴侣|]', 'en': '[|AI|]'}

import logging
import os

def build_prompt_with_search_memory_llamaindex(history, text, user_memory, user_name, user_memory_index, service_context, api_keys, api_index, meta_prompt, new_user_meta_prompt, data_args, boot_actual_name):
    logging.info(f"Processing query for user: {user_name}")

    total_memories = len(user_memory_index.docstore.docs) if user_memory_index and hasattr(user_memory_index, 'docstore') else 0
    logging.info(f"Total memories in index: {total_memories}")

    logging.info(f"Memory file path: {os.path.join(data_args.memory_basic_dir, data_args.memory_file)}")
    logging.info(f"User memory index exists: {user_memory_index is not None}")

    memory_search_query = f'The most relevant content to the question "{text}" is:'
    if user_memory_index:
        try:
            related_memos = user_memory_index.query(memory_search_query, service_context=service_context, similarity_top_k=5)  # Increase top_k to retrieve more memories
            related_memos_content = []
            for node in related_memos.source_nodes:
                related_memos_content.append(node.text)
            related_memos = "\n\n".join(related_memos_content)
        except Exception as e:
            logging.error(f"Error during memory retrieval: {e}")
            related_memos = ''
    else:
        related_memos = ''

    logging.info(f"Number of relevant memories retrieved: {len(related_memos_content) if related_memos else 0}")
    logging.info(f"Relevant memories content: {related_memos}")

    if "overall_history" in user_memory:
        history_summary = f"The summary of your past memories with the user is: {user_memory['overall_history']}"
        related_memory_content = f"\n{str(related_memos).strip()}\n"
    else:
        history_summary = ''
        related_memory_content = ''

    personality = user_memory.get('overall_personality', "")

    if related_memos:
        prompt = meta_prompt.format(user_name=user_name, history_summary=history_summary, related_memory_content=related_memory_content, personality=personality, boot_actual_name=boot_actual_name)
    else:
        prompt = new_user_meta_prompt.format(user_name=user_name, boot_actual_name=boot_actual_name)

    return prompt, related_memos
