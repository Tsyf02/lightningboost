import os
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEndpoint

def generate_tips(metrics_data):
    ram_percent = metrics_data.get('ram_percent', 0)
    cpu_percent = metrics_data.get('cpu_percent', 0)
    status = metrics_data.get('status', 'OK')

    try:
        # Initialize a placeholder HuggingFace Endpoint. 
        # Note: This will fail without a real HUGGINGFACEHUB_API_TOKEN, triggering our fallback logic.
        llm = HuggingFaceEndpoint(
            repo_id="HuggingFaceH4/zephyr-7b-beta",
            task="text-generation",
            max_new_tokens=100,
        )

        template = "You are an AI system optimizer. The user's laptop is currently at {ram_percent}% RAM usage and {cpu_percent}% CPU usage. The system status is {status}. Generate 3 short, aggressive terminal commands or actions to free up memory immediately."
        
        prompt = PromptTemplate(
            input_variables=["ram_percent", "cpu_percent", "status"],
            template=template,
        )

        chain = prompt | llm
        
        response = chain.invoke({
            "ram_percent": ram_percent,
            "cpu_percent": cpu_percent,
            "status": status
        })
        
        # Clean up the output to return a list
        tips = [tip.strip() for tip in response.strip().split('\n') if tip.strip()]
        if not tips:
            raise ValueError("Empty response from LLM")
            
        return tips

    except Exception as e:
        print(f"LangChain LLM generation failed ({e}). Falling back to static tips.")
        # Graceful fallback
        if ram_percent > 80:
            return [
                "Kill background browser processes",
                "Clear pip cache",
                "Offload current task to AMD Cloud"
            ]
        else:
            return [
                "System is optimal",
                "Ready for workloads"
            ]
