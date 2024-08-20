from flask import Flask, request, jsonify
import os, json, time
from dotenv import load_dotenv
from cli_llamaindex import predict_new
import openai
from utils.sys_args import data_args
from utils.memory_utils import enter_name_llamaindex, save_local_memory, sync_memory_index
from llama_index import LLMPredictor, PromptHelper, ServiceContext
from langchain.chat_models import ChatOpenAI
from memory_bank.build_memory_index import build_memory_index
from memory_bank.custom_index import CustomGPTSimpleVectorIndex

import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='memory_bank.log',
                    filemode='a')
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# Global variables
users = {}
memory = json.load(open(os.path.join(data_args.memory_basic_dir, data_args.memory_file), "r", encoding="utf-8"))

# Initialize LLMPredictor and ServiceContext
llm_predictor = LLMPredictor(llm=ChatOpenAI(model_name="gpt-4-turbo"))
max_input_size = 4096
num_output = 256
max_chunk_overlap = 20
prompt_helper = PromptHelper(max_input_size, num_output, max_chunk_overlap)
service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor, prompt_helper=prompt_helper)

@app.route('/initialize', methods=['POST'])
def initialize():
    data = request.get_json()
    user_id = data['user_id']

    logging.info(f"Initializing user: {user_id}")

    if user_id not in users:
        # Create a fresh memory for the new user
        fresh_memory = {user_id: {"name": user_id, "history": {}}}

        llm_predictor = LLMPredictor(llm=ChatOpenAI(model_name="gpt-4-turbo"))
        prompt_helper = PromptHelper(max_input_size=4096, num_output=512, max_chunk_overlap=50)
        service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor, prompt_helper=prompt_helper)

        users[user_id] = {
            "history": [],
            "user_memory": None,
            "user_memory_index": CustomGPTSimpleVectorIndex([], service_context=service_context),
        }

        # Pass the fresh memory to enter_name_llamaindex
        hello_msg, user_memory, user_memory_index = enter_name_llamaindex(user_id, fresh_memory, users[user_id]["user_memory_index"], data_args)

        users[user_id]["user_memory"] = user_memory

        # Update the global memory with the new user's fresh memory
        memory.update(fresh_memory)

        # Save the updated memory to file
        save_local_memory(memory, [], user_id, data_args)

        logging.info(f"Created fresh memory for new user: {user_id}")
    else:
        logging.info(f"User already initialized: {user_id}")

    logging.info(f"User initialized: {user_id}")
    logging.info(f"User memory index exists: {users[user_id]['user_memory_index'] is not None}")

    return jsonify({"response": f"Initialized user {user_id}"})

@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    user_id = data['user_id']
    query_text = data['query']

    if user_id not in users:
        return jsonify({"error": "User not initialized"}), 400

    user_data = users[user_id]

    history_state, history, msg = predict_new(
        text=query_text,
        history=user_data["history"],
        top_p=0.95,
        temperature=1,
        max_length_tokens=2000,
        max_context_length_tokens=4000,
        user_name=user_id,
        user_memory=user_data["user_memory"],
        user_memory_index=user_data["user_memory_index"],
        service_context=service_context,
        api_index=0
    )

    user_data["history"] = history

    # Save only the latest interaction
    latest_interaction = {'query': query_text, 'response': history_state[-1]['response']}
    save_local_memory(memory, latest_interaction, user_id, data_args)

    # Rebuild index after saving new memory
    user_data["user_memory_index"] = build_memory_index(memory, data_args, user_data["user_memory_index"], name=user_id)

    return jsonify({"response": history_state[-1]['response']})

@app.route('/reset', methods=['POST'])
def reset():
    data = request.get_json()
    user_id = data['user_id']
    if user_id in users:
        del users[user_id]
    return jsonify({"status": "reset"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
