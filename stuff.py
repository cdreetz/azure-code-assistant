import os
import json
import duckdb
from typing import Dict, List, Any, Optional
from openai import AzureOpenAI
from datetime import datetime

# Initialize the Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2025-02-01-preview"
)

# Define the deployment you want to use
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Database configuration
DB_PATH = "company_data.db"  # Path to your DuckDB database
SCHEMA_PATH = "table_descriptions.json"  # Path to your table schema descriptions

class DatabaseQueryAgent:
    def __init__(self, db_path: str, schema_path: str):
        """Initialize the database agent with paths to the database and schema description."""
        self.conn = duckdb.connect(db_path)
        self.schema = self._load_schema(schema_path)
        
    def _load_schema(self, schema_path: str) -> Dict:
        """Load the database schema description from a JSON file."""
        with open(schema_path, 'r') as f:
            return json.load(f)
    
    def get_schema_description(self) -> str:
        """Format the schema into a string for the AI prompt."""
        description = "DATABASE SCHEMA:\n\n"
        
        for table_name, table_info in self.schema.items():
            description += f"Table: {table_name}\n"
            description += f"Description: {table_info['description']}\n"
            description += "Fields:\n"
            
            for field in table_info['fields']:
                field_desc = f"- {field['name']} ({field['type']})"
                if 'description' in field:
                    field_desc += f": {field['description']}"
                description += field_desc + "\n"
            
            description += "\n"
            
        return description

    def execute_query(self, query: str) -> List[Dict]:
        """Execute a SQL query and return results as a list of dictionaries."""
        try:
            result = self.conn.execute(query).fetchall()
            columns = [col[0] for col in self.conn.execute(query).description]
            
            # Convert to list of dictionaries
            return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            return [{"error": str(e)}]

def build_query(query_structure: Dict) -> str:
    """Convert a query structure to a SQL query."""
    # Basic SELECT and FROM
    columns = ", ".join(query_structure.get("columns", ["*"]))
    table = query_structure.get("table", "")
    
    if not table:
        return "-- Error: No table specified"
    
    sql = f"SELECT {columns} FROM {table}"
    
    # Add JOINs if present
    if "joins" in query_structure and query_structure["joins"]:
        for join in query_structure["joins"]:
            join_table = join.get("table", "")
            join_type = join.get("type", "INNER").upper()
            join_conditions = join.get("on", {})
            left_col = join_conditions.get("left_column", "")
            right_col = join_conditions.get("right_column", "")
            sql += f" {join_type} JOIN {join_table} ON {table}.{left_col} = {join_table}.{right_col}"
    
    # Add WHERE conditions if present
    if "conditions" in query_structure and query_structure["conditions"]:
        conditions = []
        for condition in query_structure["conditions"]:
            column = condition.get("column", "")
            operator = condition.get("operator", "=")
            value = condition.get("value", "")
            
            # Format value based on type (string, number, etc.)
            if isinstance(value, str) and not value.lower().startswith("select"):
                formatted_value = f"'{value}'"
            else:
                formatted_value = str(value)
            
            conditions.append(f"{column} {operator} {formatted_value}")
        
        sql += " WHERE " + " AND ".join(conditions)
    
    # Add GROUP BY if present
    if "group_by" in query_structure and query_structure["group_by"]:
        group_by_cols = ", ".join(query_structure["group_by"])
        sql += f" GROUP BY {group_by_cols}"
    
    # Add ORDER BY if present
    if "order_by" in query_structure and query_structure["order_by"]:
        order_clauses = []
        for order in query_structure["order_by"]:
            column = order.get("column", "")
            direction = order.get("direction", "ASC")
            order_clauses.append(f"{column} {direction}")
        
        sql += f" ORDER BY {', '.join(order_clauses)}"
    
    # Add LIMIT if present
    if "limit" in query_structure and query_structure["limit"]:
        sql += f" LIMIT {query_structure['limit']}"
    
    return sql

def process_user_question(question: str) -> str:
    """Process a user question using the OpenAI tool calling approach."""
    # Initialize the database agent
    agent = DatabaseQueryAgent(DB_PATH, SCHEMA_PATH)
    schema_description = agent.get_schema_description()
    
    # Define the tools that OpenAI can use
    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_database",
                "description": "Generate a database query structure based on the user's question",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "string",
                            "description": "The primary table to query"
                        },
                        "columns": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of columns to select"
                        },
                        "conditions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {
                                        "type": "string",
                                        "description": "Column name for the condition"
                                    },
                                    "operator": {
                                        "type": "string",
                                        "description": "Operator for the condition (=, >, <, etc.)"
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "Value to compare against"
                                    }
                                },
                                "required": ["column", "operator", "value"]
                            },
                            "description": "Conditions for the WHERE clause"
                        },
                        "joins": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "table": {
                                        "type": "string",
                                        "description": "Table to join with"
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "Type of join (INNER, LEFT, RIGHT, etc.)"
                                    },
                                    "on": {
                                        "type": "object",
                                        "properties": {
                                            "left_column": {
                                                "type": "string",
                                                "description": "Column from the primary table"
                                            },
                                            "right_column": {
                                                "type": "string",
                                                "description": "Column from the joined table"
                                            }
                                        },
                                        "required": ["left_column", "right_column"]
                                    }
                                },
                                "required": ["table", "on"]
                            },
                            "description": "Joins with other tables"
                        },
                        "group_by": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Columns to group by"
                        },
                        "order_by": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {
                                        "type": "string",
                                        "description": "Column to order by"
                                    },
                                    "direction": {
                                        "type": "string",
                                        "description": "Direction (ASC or DESC)"
                                    }
                                },
                                "required": ["column"]
                            },
                            "description": "Columns to order by"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Limit the number of results"
                        }
                    },
                    "required": ["table"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_query",
                "description": "Execute a SQL query against the database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SQL query to execute"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    # Initial user message with schema information
    messages = [
        {"role": "system", "content": f"You are a helpful database assistant that helps users query a database. Here is the database schema:\n\n{schema_description}"},
        {"role": "user", "content": question}
    ]
    
    # First API call: Ask the model to determine which query to execute
    response = client.chat.completions.create(
        model=deployment_name,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    
    # Process the model's response
    response_message = response.choices[0].message
    messages.append(response_message)
    
    # Handle function calls
    query_results = None
    
    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name == "query_database":
                # Build the SQL query from the structured output
                sql_query = build_query(function_args)
                
                # Log the query for debugging
                print(f"Generated SQL Query: {sql_query}")
                
                # Add the tool call response
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": "query_database",
                    "content": json.dumps({"query": sql_query})
                })
                
                # Execute query on the next API call
                follow_up_response = client.chat.completions.create(
                    model=deployment_name,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                
                follow_up_message = follow_up_response.choices[0].message
                messages.append(follow_up_message)
                
                # Process the execute_query function call
                if follow_up_message.tool_calls:
                    for follow_tool_call in follow_up_message.tool_calls:
                        if follow_tool_call.function.name == "execute_query":
                            execute_args = json.loads(follow_tool_call.function.arguments)
                            query = execute_args.get("query")
                            
                            # Execute the query
                            query_results = agent.execute_query(query)
                            
                            # Add the results to the messages
                            messages.append({
                                "tool_call_id": follow_tool_call.id,
                                "role": "tool",
                                "name": "execute_query",
                                "content": json.dumps(query_results)
                            })
            
            elif function_name == "execute_query":
                # Direct execution (might happen if the model decides to execute immediately)
                query = function_args.get("query")
                
                # Execute the query
                query_results = agent.execute_query(query)
                
                # Add the results to the messages
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": "execute_query",
                    "content": json.dumps(query_results)
                })
    
    # Final API call: Get the final response from the model
    final_response = client.chat.completions.create(
        model=deployment_name,
        messages=messages,
    )
    
    return {
        "answer": final_response.choices[0].message.content,
        "query_results": query_results
    }

def run_example():
    """Run an example question."""
    question = "What was the budget for Engineering department in 2023?"
    print(f"Question: {question}")
    
    result = process_user_question(question)
    
    print("\nAnswer:")
    print(result["answer"])
    
    print("\nQuery Results:")
    print(json.dumps(result["query_results"], indent=2))

if __name__ == "__main__":
    run_example()


import os
import json
import duckdb
from openai import AzureOpenAI
from typing import Dict, List

# Configure your environment variables before running
# os.environ["AZURE_OPENAI_ENDPOINT"] = "your-endpoint"
# os.environ["AZURE_OPENAI_API_KEY"] = "your-api-key"
# os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "your-deployment-name"

# Initialize the Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2025-02-01-preview"
)

# Define the deployment to use
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Database paths
DB_PATH = "company_data.db"
SCHEMA_PATH = "table_descriptions.json"

class SimplifiedDBAgent:
    def __init__(self, db_path: str, schema_path: str):
        self.conn = duckdb.connect(db_path)
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
    
    def get_schema_description(self) -> str:
        """Format the schema for the prompt."""
        description = "DATABASE SCHEMA:\n\n"
        for table_name, table_info in self.schema.items():
            description += f"Table: {table_name}\n"
            description += f"Description: {table_info['description']}\n"
            description += "Fields:\n"
            for field in table_info['fields']:
                description += f"- {field['name']} ({field['type']}): {field.get('description', '')}\n"
            description += "\n"
        return description
    
    def execute_query(self, query: str) -> List[Dict]:
        """Execute a SQL query and return results."""
        try:
            result = self.conn.execute(query).fetchall()
            columns = [col[0] for col in self.conn.execute(query).description]
            return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            return [{"error": str(e)}]

def query_database(table: str, columns: List[str], conditions: List[Dict] = None, 
                  joins: List[Dict] = None, group_by: List[str] = None, 
                  order_by: List[Dict] = None, limit: int = None) -> Dict:
    """Tool function for the model to generate a query structure."""
    query_structure = {
        "table": table,
        "columns": columns
    }
    
    if conditions:
        query_structure["conditions"] = conditions
    if joins:
        query_structure["joins"] = joins
    if group_by:
        query_structure["group_by"] = group_by
    if order_by:
        query_structure["order_by"] = order_by
    if limit:
        query_structure["limit"] = limit
    
    # Build SQL query from the structure
    sql = build_sql_query(query_structure)
    
    return {
        "structure": query_structure,
        "sql": sql
    }

def build_sql_query(query_structure: Dict) -> str:
    """Convert query structure to SQL."""
    columns = ", ".join(query_structure.get("columns", ["*"]))
    table = query_structure.get("table", "")
    sql = f"SELECT {columns} FROM {table}"
    
    # Add JOINs
    if "joins" in query_structure and query_structure["joins"]:
        for join in query_structure["joins"]:
            join_table = join.get("table", "")
            join_type = join.get("type", "INNER").upper()
            left_col = join.get("on", {}).get("left_column", "")
            right_col = join.get("on", {}).get("right_column", "")
            sql += f" {join_type} JOIN {join_table} ON {table}.{left_col} = {join_table}.{right_col}"
    
    # Add WHERE conditions
    if "conditions" in query_structure and query_structure["conditions"]:
        conditions = []
        for condition in query_structure["conditions"]:
            column = condition.get("column", "")
            operator = condition.get("operator", "=")
            value = condition.get("value", "")
            
            # Format value based on type
            if isinstance(value, str) and not value.lower().startswith("select"):
                formatted_value = f"'{value}'"
            else:
                formatted_value = str(value)
            
            conditions.append(f"{column} {operator} {formatted_value}")
        
        sql += " WHERE " + " AND ".join(conditions)
    
    # Add GROUP BY
    if "group_by" in query_structure and query_structure["group_by"]:
        sql += f" GROUP BY {', '.join(query_structure['group_by'])}"
    
    # Add ORDER BY
    if "order_by" in query_structure and query_structure["order_by"]:
        order_clauses = []
        for order in query_structure["order_by"]:
            column = order.get("column", "")
            direction = order.get("direction", "ASC")
            order_clauses.append(f"{column} {direction}")
        
        sql += f" ORDER BY {', '.join(order_clauses)}"
    
    # Add LIMIT
    if "limit" in query_structure and query_structure["limit"]:
        sql += f" LIMIT {query_structure['limit']}"
    
    return sql

def execute_query(query: str) -> List[Dict]:
    """Tool function to execute the SQL query."""
    agent = SimplifiedDBAgent(DB_PATH, SCHEMA_PATH)
    return agent.execute_query(query)

def process_question(question: str) -> Dict:
    """Process a user question using tool calling."""
    agent = SimplifiedDBAgent(DB_PATH, SCHEMA_PATH)
    schema_description = agent.get_schema_description()
    
    # Define the tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_database",
                "description": "Generate a database query structure based on the user's question",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "string",
                            "description": "The primary table to query"
                        },
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of columns to select"
                        },
                        "conditions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "operator": {"type": "string"},
                                    "value": {"type": "string"}
                                },
                                "required": ["column", "operator", "value"]
                            },
                            "description": "WHERE conditions"
                        },
                        "joins": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "table": {"type": "string"},
                                    "type": {"type": "string"},
                                    "on": {
                                        "type": "object",
                                        "properties": {
                                            "left_column": {"type": "string"},
                                            "right_column": {"type": "string"}
                                        },
                                        "required": ["left_column", "right_column"]
                                    }
                                },
                                "required": ["table", "on"]
                            }
                        },
                        "group_by": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "order_by": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "direction": {"type": "string"}
                                },
                                "required": ["column"]
                            }
                        },
                        "limit": {"type": "integer"}
                    },
                    "required": ["table", "columns"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_query",
                "description": "Execute a SQL query against the database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SQL query to execute"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    # Initial conversation
    messages = [
        {"role": "system", "content": f"You are a database assistant. Based on the user's question, determine the appropriate database query to execute.\n\n{schema_description}"},
        {"role": "user", "content": question}
    ]
    
    # First call: Generate query structure
    response = client.chat.completions.create(
        model=deployment_name,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    
    response_message = response.choices[0].message
    messages.append(response_message)
    
    # Track results
    results = {
        "question": question,
        "sql_query": None,
        "query_results": None,
        "final_answer": None
    }
    
    # Process tool calls
    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name == "query_database":
                # Extract the query structure and build SQL query
                query_structure = {
                    "table": function_args.get("table"),
                    "columns": function_args.get("columns", ["*"]),
                    "conditions": function_args.get("conditions", []),
                    "joins": function_args.get("joins", []),
                    "group_by": function_args.get("group_by", []),
                    "order_by": function_args.get("order_by", []),
                    "limit": function_args.get("limit")
                }
                
                sql_query = build_sql_query(query_structure)
                results["sql_query"] = sql_query
                
                # Add the generated SQL to messages
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": "query_database",
                    "content": json.dumps({"sql": sql_query})
                })
                
                # Execute the query with a second tool call
                follow_up = client.chat.completions.create(
                    model=deployment_name,
                    messages=messages,
                    tools=tools,
                    tool_choice={"type": "function", "function": {"name": "execute_query"}}
                )
                
                follow_message = follow_up.choices[0].message
                messages.append(follow_message)
                
                # Process the execute_query call
                if follow_message.tool_calls:
                    for exec_call in follow_message.tool_calls:
                        if exec_call.function.name == "execute_query":
                            exec_args = json.loads(exec_call.function.arguments)
                            query = exec_args.get("query")
                            
                            # Execute the query and get results
                            query_results = agent.execute_query(query)
                            results["query_results"] = query_results
                            
                            # Add results to messages
                            messages.append({
                                "tool_call_id": exec_call.id,
                                "role": "tool",
                                "name": "execute_query",
                                "content": json.dumps(query_results)
                            })
    
    # Final call: Get the answer
    final_response = client.chat.completions.create(
        model=deployment_name,
        messages=messages,
    )
    
    results["final_answer"] = final_response.choices[0].message.content
    return results

def run_demo():
    """Run the demo with multiple example questions."""
    questions = [
        "What was the budget for Engineering department in 2023?",
        "How does the Marketing department's 2023 budget compare to its 2022 budget?",
        "Which department had the highest budget in 2023?",
        "What is the total budget across all departments for 2023?",
        "How much did the Research department spend on equipment in 2023?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*80}\nQUESTION {i}: {question}\n{'='*80}\n")
        
        results = process_question(question)
        
        print(f"SQL Query: {results['sql_query']}\n")
        print(f"Query Results: {json.dumps(results['query_results'], indent=2)}\n")
        print(f"Answer: {results['final_answer']}\n")

if __name__ == "__main__":
    run_demo()
