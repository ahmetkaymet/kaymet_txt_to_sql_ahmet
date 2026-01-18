"""
ACE Core Integration Patch for langchain_utils.py
Bu dosyayı langchain_utils.py'ye ekleyebilir veya modifiye edebilirsin
"""

# langchain_utils.py dosyasının başına ekle:
"""
# ACE Core Integration (başa ekle)
try:
    from ace_core_integration import get_ace_instance
    ACE_ENABLED = True
except ImportError:
    ACE_ENABLED = False
    logger.warning("ACE Core not available. Install with: pip install git+https://github.com/ahmetererr/ace_lib.git")
"""

# process_natural_query_langchain fonksiyonunu şu şekilde güncelle:

"""
async def process_natural_query_langchain(natural_query: str, session_id: str = None):
    # ... mevcut kod ...
    
    # ACE Integration - SQL generation'dan önce
    ace_context = ""
    query_type = None
    
    if ACE_ENABLED:
        try:
            ace_sql = get_ace_instance()
            
            # Detect query type (basit detection)
            if any(word in natural_query.lower() for word in ["çalışan", "employee", "toplam", "count"]):
                query_type = "employee_count"
            elif any(word in natural_query.lower() for word in ["departman", "department"]):
                query_type = "department_analysis"
            elif any(word in natural_query.lower() for word in ["izin", "leave"]):
                query_type = "leave_analysis"
            
            # Get ACE context
            ace_context = ace_sql.get_sql_context(query_type=query_type, max_items=15)
            logger.info(f"ACE context retrieved: {len(ace_context)} chars")
        except Exception as e:
            logger.warning(f"ACE context retrieval failed: {e}")
    
    # Mevcut context'e ACE context'i ekle
    # ruleset_context = get_ruleset_context()  # Mevcut
    # full_context = f"{ace_context}\n\n{ruleset_context}" if ace_context else ruleset_context
    
    # ... SQL generation (mevcut kod) ...
    
    # SQL execution'dan sonra ACE ile öğren
    if ACE_ENABLED and query_type:
        try:
            ace_sql = get_ace_instance()
            
            # Build execution feedback
            execution_feedback = {
                "rows_returned": len(result_data) if result_data else 0,
                "execution_time_ms": (time.time() - start_time) * 1000,
                "success": True
            }
            
            # Learn from query
            ace_sql.learn_from_query(
                natural_query=natural_query,
                generated_sql=sql_query,
                executed_sql=sql_query,
                success=True,
                execution_feedback=execution_feedback,
                query_type=query_type
            )
            
            logger.info(f"ACE learning completed for query type: {query_type}")
        except Exception as e:
            logger.warning(f"ACE learning failed: {e}")
    
    # ... mevcut return statement ...
"""
