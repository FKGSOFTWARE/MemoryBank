from llama_index import Document, GPTVectorStoreIndex
from llama_index.data_structs.node_v2 import Node
from llama_index.docstore import SimpleDocumentStore
from llama_index.docstore.utils import json_to_doc
from llama_index.vector_stores.types import NodeEmbeddingResult
from llama_index.vector_stores.simple import SimpleVectorStore
import logging
import json

from pydantic.fields import defaultdict


class CustomGPTSimpleVectorIndex(GPTVectorStoreIndex):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensuring that vector store is initialized only once and properly passed
        if '_vector_store' not in self.__dict__ or self._vector_store is None:
            self._vector_store = SimpleVectorStore()
            logging.info(f"Vector store initialized: {self._vector_store}")
        else:
            logging.info(f"Using existing vector store: {self._vector_store}")

    @classmethod
    def load_from_disk(cls, save_path: str, **kwargs):
        with open(save_path, 'r') as f:
            data = json.load(f)

        vector_store = SimpleVectorStore(simple_vector_store_data_dict=data.get('vector_store', {}).get("simple_vector_store_data_dict", {}))
        docstore = data.get('docstore', {})
        rdi = defaultdict(dict)
        for k, v in docstore.get("ref_doc_info", {}).items():
            rdi[k] = v

        docs_dict = {}
        for i, d in docstore.get("docs", {}).items():
            docs_dict[i] = json_to_doc(d)


        # print(f"data: {docstore.get('docs', {})}")
        # print(f"docs dict: {docs_dict}")
        index = cls(nodes=[], vector_store=vector_store, **kwargs)
        index._docstore = SimpleDocumentStore(docs=docs_dict, ref_doc_info=rdi)

        return index

    def save_to_disk(self, save_path: str):
        data = {
            'vector_store': self._vector_store.config_dict,
            'docstore': self.docstore.to_dict()
        }
        with open(save_path, 'w') as f:
            json.dump(data, f)

    def insert(self, document: Document) -> None:
        """Insert a document into the index."""
        try:
            logging.info(f"Document content before processing: {document.text[:100]}")

            nodes = self._service_context.node_parser.get_nodes_from_documents([document])

            for node in nodes:
                logging.info(f"Node content: {node.get_text()[:100]}")
                embedding_results = self._service_context.embed_model.get_text_embedding(
                    node.get_text()
                )
                self._vector_store.add(
                    [NodeEmbeddingResult(node=node, embedding=embedding_results, id=node.doc_hash, doc_id=node.doc_id)]
                )
                self.docstore.add_documents([node], allow_update=True)
            logging.info(f"Inserted document into index. Current size: {len(self.docstore.docs)}")

        except TypeError as e:
            logging.error(f"Type error: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Failed to insert document: {str(e)}")
            raise



    def get_vector_store_info(self):
        """Get information about the vector store."""
        total_documents = len(self.docstore.docs)

        if self._vector_store:
            # Use the _data attribute of SimpleVectorStore
            total_embeddings = len(self._vector_store._data.embedding_dict)
        else:
            total_embeddings = 0
            logging.warning("Vector store is not initialized.")

        return {
            "total_documents": total_documents,
            "total_embeddings": total_embeddings,
        }
