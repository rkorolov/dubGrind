import os
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

def summarize_file(file_path):
    """
    Summarize the content of a file using LangChain and OpenAI.

    Args:
        file_path (str): The path to the file to summarize.

    Returns:
        str: The summarized content of the file.
    """
    # Load environment variables
    load_dotenv()

    # Get the OpenAI API key
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("Please set the OPENAI_API_KEY environment variable")

    # Load file content
    loader = PyPDFLoader(file_path)
    docs = loader.load()

    # Initialize the LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.9)

    # Define prompt
    prompt = ChatPromptTemplate.from_messages(
        [("system", "Write a concise summary and an overarching takeaways section at the end of the following, such as topics to focus on. (do not include next steps):\n\n{context}")]
    )

    # Create chain
    chain = create_stuff_documents_chain(llm, prompt)

    # Invoke chain
    result = chain.invoke({"context": docs})

    return result

# Example usage
if __name__ == "__main__":
    file_path = "week4.pdf"
    summary = summarize_file(file_path)
    print(summary)