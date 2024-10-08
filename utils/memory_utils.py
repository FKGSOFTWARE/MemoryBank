import os, shutil, datetime, time, json
import gradio as gr
import sys
import os
from llama_index import GPTSimpleVectorIndex
bank_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../memory_bank')
sys.path.append(bank_path)
from build_memory_index import build_memory_index
memory_bank_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../memory_bank')
sys.path.append(memory_bank_path)
from summarize_memory import summarize_memory
import logging
import os
from llama_index import GPTSimpleVectorIndex
from memory_bank.build_memory_index import build_memory_index
from memory_bank.custom_index import CustomGPTSimpleVectorIndex

def enter_name(name, memory,local_memory_qa,data_args,update_memory_index=True):
    cur_date = datetime.date.today().strftime("%Y-%m-%d")
    user_memory_index = None
    if isinstance(data_args,gr.State):
        data_args = data_args.value
    if isinstance(memory,gr.State):
        memory = memory.value
    if isinstance(local_memory_qa,gr.State):
        local_memory_qa=local_memory_qa.value
    memory_dir = os.path.join(data_args.memory_basic_dir,data_args.memory_file)
    if name in memory.keys():
        user_memory = memory[name]
        memory_index_path = os.path.join(data_args.memory_basic_dir,f'memory_index/{name}_index')
        os.makedirs(os.path.dirname(memory_index_path), exist_ok=True)
        if (not os.path.exists(memory_index_path)) or update_memory_index:
            print(f'Initializing memory index {memory_index_path}...')
        # filepath = input("Input your local knowledge file path 请输入本地知识文件路径：")
            if os.path.exists(memory_index_path):
                shutil.rmtree(memory_index_path)
            memory_index_path, _ = local_memory_qa.init_memory_vector_store(filepath=memory_dir,vs_path=memory_index_path,user_name=name,cur_date=cur_date)

        user_memory_index = local_memory_qa.load_memory_index(memory_index_path) if memory_index_path else None
        msg = f"欢迎回来，{name}！" if data_args.language=='cn' else f"Wellcome Back, {name}！"
        return msg,user_memory,memory, name,user_memory_index
    else:
        memory[name] = {}
        memory[name].update({"name":name})
        msg = f"欢迎新用户{name}！我会记住你的名字，下次见面就能叫你的名字啦！" if data_args.language == 'cn' else f'Welcome, new user {name}! I will remember your name, so next time we meet, I\'ll be able to call you by your name!'
        return msg,memory[name],memory,name,user_memory_index

def enter_name_llamaindex(name, memory, data_args, update_memory_index=True):
    logging.info(f"Entering enter_name_llamaindex for user: {name}")

    user_memory_index = None
    memory_index_path = os.path.join(data_args.memory_basic_dir, 'memory_index', f'{name}_index.json')

    logging.info(f"Memory index path: {memory_index_path}")
    logging.info(f"Memory index exists: {os.path.exists(memory_index_path)}")
    logging.info(f"Update memory index flag: {update_memory_index}")

    if name in memory.keys():
        user_memory = memory[name]
    else:
        logging.info(f"New user: {name}")
        user_memory = memory[name] = {
            "name": name,
            "history": {}
        }

    if not os.path.exists(memory_index_path) or update_memory_index:
        logging.info(f'Initializing memory index for {name}...')
        user_memory_index = build_memory_index(memory, data_args, name=name)
    else:
        user_memory_index = GPTSimpleVectorIndex.load_from_disk(memory_index_path)
        logging.info(f'Successfully loaded memory index for user {name}!')

    if name in memory.keys():
        return f"Welcome Back, {name}!", user_memory, user_memory_index
    else:
        return f"Welcome new user {name}! I will remember your name and call you by your name in the next conversation", user_memory, user_memory_index

def sync_memory_index(user_id, memory, data_args):
    memory_index_path = os.path.join(data_args.memory_basic_dir, 'memory_index', f'{user_id}_index.json')
    logging.info(f"Attempting to sync memory index for user {user_id}")
    logging.info(f"Memory index path: {memory_index_path}")
    logging.info(f"Memory index exists: {os.path.exists(memory_index_path)}")

    if os.path.exists(memory_index_path):
        try:
            user_memory_index = CustomGPTSimpleVectorIndex.load_from_disk(memory_index_path)
            logging.info(f"Successfully loaded memory index for user {user_id}")
            logging.info(f"Loaded index info: {user_memory_index.get_vector_store_info()}")
        except Exception as e:
            logging.error(f"Error loading index for user {user_id}: {str(e)}")
            logging.exception("Exception details:")
            logging.info(f"Rebuilding index for user {user_id}")
            user_memory_index = build_memory_index({user_id: memory[user_id]}, data_args, name=user_id)
    else:
        logging.info(f"No existing index found. Building new index for user {user_id}")
        user_memory_index = build_memory_index({user_id: memory[user_id]}, data_args, name=user_id)

    logging.info(f"Final index info: {user_memory_index.get_vector_store_info()}")
    return user_memory_index

def summarize_memory_event_personality(data_args, memory, user_name):
    if isinstance(data_args,gr.State):
        data_args = data_args.value
    if isinstance(memory,gr.State):
        memory = memory.value
    memory_dir = os.path.join(data_args.memory_basic_dir,data_args.memory_file)
    memory = summarize_memory(memory_dir,user_name,language=data_args.language)
    user_memory = memory[user_name] if user_name in memory.keys() else {}
    return user_memory#, user_memory_index

def save_local_memory(memory, history, user_id, data_args):
    logging.info(f"Saving local memory for user: {user_id}")
    memory_dir = os.path.join(data_args.memory_basic_dir, data_args.memory_file)
    logging.info(f"Memory directory: {memory_dir}")
    date = time.strftime("%Y-%m-%d", time.localtime())

    if user_id not in memory:
        memory[user_id] = {}

    if 'history' not in memory[user_id]:
        memory[user_id]['history'] = {}

    if date not in memory[user_id]['history']:
        memory[user_id]['history'][date] = []

    # Handle both list and dictionary formats for history
    if isinstance(history, list):
        for h in history:
            if isinstance(h, dict):
                memory[user_id]['history'][date].append({'query': h.get('query', ''), 'response': h.get('response', '')})
            elif isinstance(h, (list, tuple)) and len(h) == 2:
                memory[user_id]['history'][date].append({'query': h[0], 'response': h[1]})
    elif isinstance(history, dict):
        memory[user_id]['history'][date].append({'query': history.get('query', ''), 'response': history.get('response', '')})

    with open(memory_dir, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved memory for user {user_id}")
    return memory
