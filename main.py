import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
from phi.agent import Agent
from phi.storage.agent.sqlite import SqlAgentStorage
from phi.model.openai import OpenAIChat
from langchain_community.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from phi.knowledge.langchain import LangChainKnowledgeBase
from langchain.schema import Document
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.yfinance import YFinanceTools
import asyncio
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CHROMADB_PATH = "./chroma_db"

EMBEDDING_MODEL = "text-embedding-3-large"

app = FastAPI(title="Financial Chatbot", version="1.0")

# ✅ Store Chat History
session_history = {}

sophisticated_prompt = """
## Role:
You are a professional financial consultant with access to a structured database of company financial reports from AMMC.
Your goal is to provide **accurate, structured, and insightful financial analysis** using **ChromaDB**.

---

## 🔹 Response Guidelines:
1️⃣ **If the user asks for a specific company's financials**:
   - Retrieve **the exact report** from ChromaDB.
   - Provide **key financial metrics** in a **well-structured** (Revenue, Net Profit, EBITDA, Growth Rate, etc.).
   - Offer **professional insights** about trends & performance.

2️⃣ **If the user asks for comparisons**:
   - Retrieve **data for multiple companies**.
   - Compare financial metrics
   - Provide **insights** (e.g., "Company X has a stronger growth rate than Company Y").

3️⃣ **If the requested data is missing**:
   - Clearly state: *"This data is not available in the current reports."*
   - Suggest the **closest available** financial data.

   show the data in structured table or steuctured format . try to use newlines for more human readable
"""

routing_agent_prompt = """
# 🎩 AlphaFinance Virtual Assistant: Market & Finance Expert
## Role:
You are **AlphaFinance**, a professional virtual financial assistant specializing in market analysis, company financials, and investment insights. Your goal is to provide **structured, data-driven insights** in a **consulting approach**.

---

## Routing:
"If the query is about RAG or related topics, route it to the Knowledge Base Agent.",
"If the query is about recent news or information, route it to the Web Search Agent.",
"Please provide me directly the meaningful information",

## 🔹 Communication Style:
- 💼 **Professional & Friendly:** Maintain a smooth, polite, and helpful tone.
- 🔍 **Concise & Structured:** Deliver clear insights, avoid unnecessary details.
- 📊 **Data-Driven:** Always back responses with financial facts and numbers.


## 🔹 What You Can Discuss:
You **ONLY** answer **finance-related queries**. If a query is **off-topic**, politely redirect the user.
1️⃣ 📊 **Company Financials** (Revenue, Profit, Liabilities, Growth Trends)  
2️⃣ 🔍 **Investment Analysis** (Stocks, Market Positioning, Financial Ratios)  
3️⃣ 📉 **Market Trends & Economic Insights**  
4️⃣ 💡 **Comparative Financial Analysis**  
5️⃣ 🏦 **Regulatory Compliance (AMMC & Stock Exchange Rules)**  
6️⃣ 📌 **Macroeconomic Indicators (Inflation, Interest Rates, GDP Growth)**  
show the data in structured table or steuctured format . try to use newlines for more human readable
"""




vector_db = Chroma(persist_directory="./chroma_db", embedding_function=OpenAIEmbeddings(model="text-embedding-3-large", openai_api_key=OPENAI_API_KEY))
retriever = vector_db.as_retriever()
knowledge_base = LangChainKnowledgeBase(retriever=retriever)

storage = SqlAgentStorage(table_name="agent_sessions", db_file="tmp/agent_storage.db")


knowledge_agent = Agent(
        model=OpenAIChat(id='gpt-4o-mini'),
        name="Financial Analyst",
        role="An AI financial analyst that retrieves company financial reports.",
        instructions=[sophisticated_prompt],
        knowledge=knowledge_base,
        add_context=True,
        search_knowledge=True,
        markdown=True,
    )

web_search_agent = Agent(
    name="Web Search Agent",
    role="Searches the web for the latest news and information.",
    tools=[DuckDuckGo()],
    model=OpenAIChat(id="gpt-4o-mini"),
)

finance_agent = Agent(
    name="Finance Agent",
    role="Handles financial queries, such as stock prices and market trends.",
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)],
    model=OpenAIChat(id="gpt-4o-mini"),
)

content_writer_agent = Agent(
    name="Content Writer Agent",
    role="Generates engaging blogs, articles, and other written content.",
    model=OpenAIChat(id="gpt-4o-mini"),
)

router_agent = Agent(
    name="Router Agent",
    role="Routes user queries to the appropriate agent.",
    instructions=[routing_agent_prompt],
    storage=storage,
    add_chat_history_to_messages=True,
    um_history_responses=3,  
    team=[knowledge_agent, web_search_agent, finance_agent, content_writer_agent],
    show_tool_calls=False,
    markdown=True,
)

session_history = {}

# class ChatRequest(BaseModel):
#     session_id: str
#     message: str

# async def async_stream(generator):
#     """
#     Converts a synchronous generator into an asynchronous generator.
#     Extracts the text from `RunResponse` before yielding.
#     """
#     for chunk in generator:
#         if hasattr(chunk, "content"):  # ✅ Extract content if it's a RunResponse
#             yield chunk.content + "\n"
#         else:
#             yield str(chunk) + "\n"
#         await asyncio.sleep(0)  # ✅ Allows FastAPI to handle async execution

# # ✅ Stream Generator Function
# async def stream_response(session_id: str, message: str):
#     """
#     Streams chatbot response token-by-token using Phidata Agent.
#     """
#     if session_id not in session_history:
#         session_history[session_id] = []

#     # ✅ Add user message to history
#     session_history[session_id].append({"role": "user", "content": message})

#     # ✅ Run the agent and get streaming response
#     generator = router_agent.run(message, stream=True)  # ✅ Enable streaming
#     # ✅ Convert to async iterator
#     return async_stream(generator)


# @app.post("/chat")
# async def chat(request: ChatRequest):
#     return StreamingResponse(await stream_response(request.session_id, request.message), media_type="text/plain")

# @app.get("/history/{session_id}")
# async def get_chat_history(session_id: str):
#     if session_id not in session_history:
#         raise HTTPException(status_code=404, detail="Session not found")
#     return {"session_id": session_id, "history": session_history[session_id]}

# @app.delete("/history/{session_id}")
# async def reset_chat_history(session_id: str):
#     if session_id in session_history:
#         del session_history[session_id]
#     return {"message": "Chat history reset"}

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    if request.session_id not in session_history:
        session_history[request.session_id] = []
    
    session_history[request.session_id].append({
        "role": "user",
        "content": request.message
    })
    
    response = router_agent.run(request.message)
    return {"response": response.content}

@app.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    if session_id not in session_history:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "history": session_history[session_id]}

@app.delete("/history/{session_id}")
async def reset_chat_history(session_id: str):
    if session_id in session_history:
        del session_history[session_id]
    return {"message": "Chat history reset"}