from llama_index import SimpleDirectoryReader, Document
from llama_index import GPTTreeIndex, GPTSimpleVectorIndex
from llama_index.indices.composability import ComposableGraph
import json, openai
from llama_index import LLMPredictor, GPTSimpleVectorIndex, PromptHelper, ServiceContext
from langchain.llms import AzureOpenAI,OpenAIChat
import os
import logging
from llama_index import GPTSimpleVectorIndex, Document
from langchain.chat_models import ChatOpenAI
from llama_index import LLMPredictor, PromptHelper, ServiceContext
from custom_index import CustomGPTSimpleVectorIndex

# language = 'en'
openai.api_key = os.environ["OPENAI_API_KEY"]
# os.environ["OPENAI_API_BASE"] = openai.api_base
# define LLM
# llm_predictor = LLMPredictor(llm=OpenAIChat(model_name="gpt-3.5-turbo"))
llm_predictor = LLMPredictor(llm=OpenAIChat(model_name="gpt-4o-mini"))

#! original!
# define prompt helper
# set maximum input size
# max_input_size = 4096
# # set number of output tokens
# num_output = 256
# # set maximum chunk overlap
# max_chunk_overlap = 20


# set maximum input size
max_input_size = 4096
# set number of output tokens
num_output = 512
# set maximum chunk overlap
max_chunk_overlap = 50

def generate_memory_docs(data, language):
    logging.info(f"Generating memory docs for users: {list(data.keys())}")
    all_user_memories = {}
    for user_name, user_memory in data.items():
        all_user_memories[user_name] = []
        if isinstance(user_memory, dict) and 'history' in user_memory:
            for date, content in user_memory['history'].items():
                for dialog in content:
                    query = dialog['query']
                    response = dialog['response']
                    memory_str = f'Date: {date}\nUser: {query.strip()}\nAI: {response.strip()}'
                    all_user_memories[user_name].append(Document(memory_str))
        elif isinstance(user_memory, list):
            for memory in user_memory:
                all_user_memories[user_name].append(Document(memory))
        else:
            logging.warning(f"Unexpected memory format for user {user_name}")
        logging.info(f"Generated {len(all_user_memories[user_name])} memories for user {user_name}")
    return all_user_memories

# all_user_memories = load_data('../memories/update_memory_0512_eng.json')

#!! Fiexs' version
index_set = {}
def build_memory_index(all_user_memories, data_args, cur_index, name=None):
    logging.info(f"Starting build_memory_index for user: {name}")

    all_user_memories = generate_memory_docs(all_user_memories, data_args.language)
    logging.info(f"Generated memory docs for users: {list(all_user_memories.keys())}")

    for user_name, user_data in all_user_memories.items():
        if name and user_name != name:
            continue

        index_path = os.path.join(data_args.memory_basic_dir, 'memory_index', f'{user_name}_index.json')

        try:
            # if os.path.exists(index_path):
            #     cur_index = CustomGPTSimpleVectorIndex.load_from_disk(index_path, service_context=service_context)
            #     logging.info(f"Loaded existing index for user {user_name}")
            # else:
            #     cur_index = CustomGPTSimpleVectorIndex([], service_context=service_context)
            #     logging.info(f"Created new index for user {user_name}")

            vector_store_info = cur_index.get_vector_store_info()
            logging.info(f"Initial index state for user {user_name}: {vector_store_info['total_documents']} documents, {vector_store_info['total_embeddings']} embeddings")

            new_memories = []
            if isinstance(user_data, list):
                for memory in user_data:
                    new_memories.append(memory)
            elif isinstance(user_data, dict) and 'history' in user_data:
                for date, conversations in user_data['history'].items():
                    for conversation in conversations:
                        memory_str = f"Date: {date}\nUser: {conversation['query']}\nAI: {conversation['response']}"
                        new_memories.append(Document(text=memory_str, extra_info={'date': date}))

            if new_memories:
                for memory in new_memories:
                    try:
                        logging.info(f"!!Memory object type: {type(memory)}")
                        logging.info(f"Attempting to insert memory: {memory.text[:100]}...")
                        cur_index.insert(memory)
                        logging.info(f"Successfully inserted memory")
                    except Exception as e:
                        logging.error(f"Failed to insert memory: {str(e)}")
                logging.info(f"Attempted to add {len(new_memories)} new memories to index for user {user_name}")

            vector_store_info = cur_index.get_vector_store_info()
            logging.info(f"Final index state for user {user_name}: {vector_store_info['total_documents']} documents, {vector_store_info['total_embeddings']} embeddings")

            cur_index.save_to_disk(index_path)
            logging.info(f"Saved updated index for user {user_name} at {index_path}")

            # Validate saved index
            # loaded_index = CustomGPTSimpleVectorIndex.load_from_disk(index_path, service_context=service_context)
            # vector_store_info = loaded_index.get_vector_store_info()
            # logging.info(f"Validated saved index for user {user_name}: {vector_store_info['total_documents']} documents, {vector_store_info['total_embeddings']} embeddings")

        except Exception as e:
            logging.error(f"Error processing memories for user {user_name}: {str(e)}")
            logging.exception("Exception details:")
            continue

    logging.info("Finished build_memory_index")
    return cur_index
