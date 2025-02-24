from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
import json
import utils


class Document:
    def __init__(self, content, metadata):
        self.content = content
        self.metadata = metadata


class DocsEmbeddingsGenerator:
    def __init__(self, model_name="BAAI/bge-small-en-v1.5", encode_kwargs={"normalize_embeddings": True}):
        self.model_name = model_name
        self.encode_kwargs = encode_kwargs
        self.embeddings = HuggingFaceEmbeddings(model_name=self.model_name, encode_kwargs=self.encode_kwargs)

    def generate_docs_embedding(self, docs):
        vectorstore = FAISS.from_documents(docs, self.embeddings)
        vectorstore.save_local("vectorstore.db")
        return vectorstore


def load_docs(directory):
    loader = DirectoryLoader(directory)
    documents = loader.load()
    return documents


def split_docs(documents, chunk_size=200, chunk_overlap=10):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = text_splitter.split_documents(documents)
    return docs


def load_and_split_documents(directory_name):
    documents = load_docs(directory_name)
    # print(f"Number of documents: {len(documents)}")
    # print(f"Number of chunks: {len(docs)}")
    if documents[0].page_content == '':
        return None
    return split_docs(documents)


def construct_prompt(question, kg_context, flag):
    template = """
                You are an assistant for question-answering tasks.
                Do not add anything, return only the answer in dictionary format.
                Use the provided context only to answer the following question:

                <context>
                {context}
                </context>

                Question: {input}
                """
    inputs = {"input": question}

    if flag:
        template = """
                    You are an assistant for question-answering tasks.
                    Do not add anything, return only the answer in dictionary format.
                    The text given the context is the institution Wikipeida text of the author under qeustion.
                    Use the provided context only to answer the following question:

                    <context>
                    {kg_context}
                    {context}
                    </context>

                    Question: {input}
                    Answer:
                    """
        inputs = {"input": question, "kg_context": kg_context}

    return inputs, template


def serialize_response(response, kg_context):
    context = []
    for doc in response['context']:
        if hasattr(doc, 'page_content'):
            context.append(doc.page_content)
        elif hasattr(doc, 'content'):
            context.append(doc.content)
        else:
            raise AttributeError('Document object has no attribute for content extraction')

    return [{'input': response['input'], 'answer': response['answer'],
             'context': [{"wikipedia_text": context, 'kg_context': kg_context}]}]


def rag_answer_generator(docs_embedding_generator, directory_name, question, kg_context=[], flag=False):
    # try:
    docs = load_and_split_documents(directory_name)
    vectorstore = docs_embedding_generator.generate_docs_embedding(docs)
    retriever = vectorstore.as_retriever()

    llm = ChatOpenAI(model_name="gpt-3.5-turbo")
    inputs, template = construct_prompt(question, kg_context, flag)
    #try:
    prompt = ChatPromptTemplate.from_template(template)
    doc_chain = create_stuff_documents_chain(llm, prompt)
    chain = create_retrieval_chain(retriever, doc_chain)
    response = chain.invoke(inputs)
    serialized_response = serialize_response(response, kg_context)
    return serialized_response



def parse_answer(answer):
    answer_json = json.loads(answer)
    answer_string = str(list(answer_json.values())[0])
    if answer_string.startswith('{') and answer_string.endswith('}'):
        return parse_answer(answer_string)
    return answer_string


if __name__ == "__main__":
    sample_questions = utils.load_json_data('sample_test.json')
    for ques in sample_questions:
        model_response = rag_answer_generator('/experiment/sample', ques['question'])
        # print(answer)
        print(model_response)
