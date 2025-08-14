"""
User Role Management System
---------------------------
Manages user permissions and query restrictions based on role levels.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User role levels with different permissions"""
    VIEWER = "viewer"           # Can only view data, no modifications
    ANALYST = "analyst"         # Can analyze data, create charts
    ADMIN = "admin"             # Full access to all features
    SUPER_ADMIN = "super_admin" # Can manage users and system

class QueryPermission(Enum):
    """Query permission levels"""
    READ_ONLY = "read_only"     # SELECT queries only
    ANALYTICAL = "analytical"   # SELECT, aggregations, charts
    FULL_ACCESS = "full_access" # All query types

class UserManager:
    """Manages user roles and permissions"""
    
    def __init__(self):
        # Demo users - production'da database'den gelecek
        self.users = {
            "demo_viewer": {
                "username": "demo_viewer",
                "role": UserRole.VIEWER,
                "permissions": QueryPermission.READ_ONLY,
                "allowed_tables": ["Stores", "Products"],  # Sadece bu tablolara erişim
                "restricted_columns": ["salary", "ssn", "credit_card"],  # Bu kolonlara erişim yok
                "max_results": 100,  # Maksimum sonuç sayısı
                "can_export": False,
                "can_create_charts": False
            },
            "demo_analyst": {
                "username": "demo_analyst", 
                "role": UserRole.ANALYST,
                "permissions": QueryPermission.ANALYTICAL,
                "allowed_tables": ["Stores", "Products", "Sales", "Customers"],
                "restricted_columns": ["salary", "ssn", "credit_card"],
                "max_results": 1000,
                "can_export": True,
                "can_create_charts": True
            },
            "demo_admin": {
                "username": "demo_admin",
                "role": UserRole.ADMIN,
                "permissions": QueryPermission.FULL_ACCESS,
                "allowed_tables": ["*"],  # Tüm tablolara erişim
                "restricted_columns": [],  # Kısıtlı kolon yok
                "max_results": 10000,
                "can_export": True,
                "can_create_charts": True
            }
        }
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        return self.users.get(username)
    
    def validate_query_permission(self, username: str, sql_query: str) -> Dict[str, Any]:
        """
        Validate if user has permission to execute this query
        
        Returns:
            Dict with validation result and any modifications needed
        """
        user = self.get_user(username)
        if not user:
            return {
                "allowed": False,
                "error": "User not found",
                "modified_query": None
            }
        
        # SQL query'yi analiz et
        sql_upper = sql_query.upper().strip()
        
        # READ_ONLY kullanıcılar için sadece SELECT izni
        if user["permissions"] == QueryPermission.READ_ONLY:
            if not sql_upper.startswith("SELECT"):
                return {
                    "allowed": False,
                    "error": f"User role '{user['role'].value}' can only execute SELECT queries",
                    "modified_query": None
                }
        
        # Tablo erişim kontrolü
        if user["allowed_tables"] != ["*"]:
            for table in user["allowed_tables"]:
                if f"FROM {table.upper()}" in sql_upper or f"JOIN {table.upper()}" in sql_upper:
                    break
            else:
                return {
                    "allowed": False,
                    "error": f"User role '{user['role'].value}' cannot access the tables in this query",
                    "modified_query": None
                }
        
        # Kısıtlı kolon kontrolü
        modified_query = sql_query
        if user["restricted_columns"]:
            for col in user["restricted_columns"]:
                if col.upper() in sql_upper:
                    # Kısıtlı kolonu SELECT'ten çıkar
                    modified_query = self._remove_restricted_column(sql_query, col)
                    logger.warning(f"Removed restricted column '{col}' from query for user {username}")
        
        # Maksimum sonuç sayısı kontrolü
        if user["max_results"] and "ROWNUM" not in sql_upper:
            modified_query = self._add_row_limit(modified_query, user["max_results"])
        
        return {
            "allowed": True,
            "error": None,
            "modified_query": modified_query,
            "user_role": user["role"].value,
            "permissions": user["permissions"].value
        }
    
    def _remove_restricted_column(self, sql_query: str, column: str) -> str:
        """Remove restricted column from SELECT statement"""
        # Basit kolon kaldırma - production'da daha gelişmiş parser kullanılmalı
        lines = sql_query.split('\n')
        modified_lines = []
        
        for line in lines:
            if line.strip().upper().startswith("SELECT"):
                # SELECT satırından kısıtlı kolonu çıkar
                if column.upper() in line.upper():
                    # Basit string replacement - production'da SQL parser kullan
                    line = line.replace(f'"{column}"', '').replace(f'{column}', '')
                    line = line.replace(', ,', ',').replace(',,', ',')
                    line = line.replace('SELECT ,', 'SELECT ').replace('SELECT,', 'SELECT ')
                modified_lines.append(line)
            else:
                modified_lines.append(line)
        
        return '\n'.join(modified_lines)
    
    def _add_row_limit(self, sql_query: str, max_rows: int) -> str:
        """Add ROWNUM limit to Oracle query"""
        if "WHERE" in sql_query.upper():
            # WHERE clause varsa ROWNUM ekle
            sql_query = sql_query.replace("WHERE", f"WHERE ROWNUM <= {max_rows} AND")
        else:
            # WHERE clause yoksa ekle
            sql_query = sql_query.rstrip() + f"\nWHERE ROWNUM <= {max_rows}"
        
        return sql_query
    
    def can_create_chart(self, username: str) -> bool:
        """Check if user can create charts"""
        user = self.get_user(username)
        return user.get("can_create_charts", False) if user else False
    
    def can_export_data(self, username: str) -> bool:
        """Check if user can export data"""
        user = self.get_user(username)
        return user.get("can_export", False) if user else False
    
    def get_user_summary(self, username: str) -> Dict[str, Any]:
        """Get user permission summary"""
        user = self.get_user(username)
        if not user:
            return {"error": "User not found"}
        
        return {
            "username": user["username"],
            "role": user["role"].value,
            "permissions": user["permissions"].value,
            "allowed_tables": user["allowed_tables"],
            "restricted_columns": user["restricted_columns"],
            "max_results": user["max_results"],
            "can_export": user["can_export"],
            "can_create_charts": user["can_create_charts"]
        }

# Global user manager instance
user_manager = UserManager()

def get_user_permissions(username: str) -> Dict[str, Any]:
    """Get user permissions for external use"""
    return user_manager.get_user_summary(username)

def validate_user_query(username: str, sql_query: str) -> Dict[str, Any]:
    """Validate user query permissions"""
    return user_manager.validate_query_permission(username, sql_query)
