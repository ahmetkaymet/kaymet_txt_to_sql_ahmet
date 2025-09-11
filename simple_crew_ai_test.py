"""
Basit CrewAI test scripti
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_simple_crew_ai():
    """Basit CrewAI testi"""
    
    try:
        from crewai import Agent, Task, Crew, Process
        from langchain_openai import ChatOpenAI
        
        print("🧪 Basit CrewAI Test")
        print("=" * 30)
        
        # LLM oluştur
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Basit agent oluştur
        agent = Agent(
            role="HR Analyst",
            goal="Analyze HR queries and generate SQL",
            backstory="You are an expert HR analyst",
            verbose=True,
            allow_delegation=False,
            llm=llm
        )
        
        # Basit task oluştur
        task = Task(
            description="Analyze this HR query: 'Kaç çalışan var?' and return a simple SQL query",
            agent=agent,
            expected_output="A simple SQL query"
        )
        
        # Crew oluştur
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        # Çalıştır
        print("🚀 CrewAI çalıştırılıyor...")
        result = crew.kickoff()
        
        print(f"✅ Sonuç: {result}")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()

def test_langchain_direct():
    """LangChain ile direkt test"""
    
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import PromptTemplate
        
        print("\n🔧 LangChain Direkt Test")
        print("=" * 30)
        
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        prompt = PromptTemplate(
            input_variables=["query"],
            template="Analyze this HR query: {query} and return a simple SQL query"
        )
        
        chain = prompt | llm
        
        result = chain.invoke({"query": "Kaç çalışan var?"})
        
        print(f"✅ LangChain Sonuç: {result}")
        
        # AIMessage handling
        if hasattr(result, 'content'):
            print(f"📝 Content: {result.content}")
        else:
            print(f"📝 Raw: {result}")
        
    except Exception as e:
        print(f"❌ LangChain Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Basit Test Suite")
    print("=" * 40)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found")
        sys.exit(1)
    
    test_langchain_direct()
    test_simple_crew_ai()
    
    print("\n🏁 Test tamamlandı!")
