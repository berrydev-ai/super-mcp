import re
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Converts natural language business questions into SuperSQL queries."""
    
    def __init__(self):
        self.query_patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, Dict]:
        """Initialize query pattern templates for common business questions."""
        return {
            "top_n": {
                "patterns": [
                    r"top\s+(\d+)\s+(.+?)\s+by\s+(.+)",
                    r"(\d+)\s+highest\s+(.+?)\s+by\s+(.+)",
                    r"best\s+(\d+)\s+(.+?)\s+by\s+(.+)"
                ],
                "template": "FROM '{s3_path}' | SUMMARIZE {metric_func}({metric}) BY {dimension} | ORDER BY {metric_func}({metric}) DESC | HEAD {limit}"
            },
            "time_series": {
                "patterns": [
                    r"(.+?)\s+by\s+(day|week|month|year|hour)",
                    r"(daily|weekly|monthly|yearly|hourly)\s+(.+)",
                    r"(.+?)\s+over\s+time"
                ],
                "template": "FROM '{s3_path}' | SUMMARIZE {metric_func}({metric}) BY date_trunc('{time_unit}', {timestamp_field}) | ORDER BY date_trunc('{time_unit}', {timestamp_field})"
            },
            "filtering": {
                "patterns": [
                    r"(.+?)\s+from\s+(.+?)\s+where\s+(.+)",
                    r"(.+?)\s+where\s+(.+)",
                    r"(.+?)\s+for\s+(.+)"
                ],
                "template": "FROM '{s3_path}' | WHERE {filter_condition} | {operation}"
            },
            "aggregation": {
                "patterns": [
                    r"average\s+(.+?)\s+by\s+(.+)",
                    r"avg\s+(.+?)\s+by\s+(.+)",
                    r"mean\s+(.+?)\s+by\s+(.+)",
                    r"sum\s+(.+?)\s+by\s+(.+)",
                    r"total\s+(.+?)\s+by\s+(.+)"
                ],
                "template": "FROM '{s3_path}' | SUMMARIZE {metric_func}({metric}) BY {dimension}"
            },
            "counting": {
                "patterns": [
                    r"how\s+many\s+(.+)",
                    r"count\s+(.+)",
                    r"number\s+of\s+(.+)"
                ],
                "template": "FROM '{s3_path}' | {filter_clause} SUMMARIZE count() {group_by}"
            }
        }
    
    async def process_query(self, natural_language: str, s3_path: str, limit: int = 100) -> str:
        """Convert natural language query to SuperSQL.
        
        Args:
            natural_language: Business question in natural language
            s3_path: S3 path to query
            limit: Result limit
            
        Returns:
            SuperSQL query string
        """
        query_lower = natural_language.lower().strip()
        
        # Try to match against known patterns
        for pattern_type, config in self.query_patterns.items():
            for pattern in config["patterns"]:
                match = re.search(pattern, query_lower)
                if match:
                    return await self._build_query(
                        pattern_type, match, config["template"], s3_path, limit
                    )
        
        # Fallback: basic query construction
        return await self._build_fallback_query(natural_language, s3_path, limit)
    
    async def _build_query(self, pattern_type: str, match: re.Match, template: str, s3_path: str, limit: int) -> str:
        """Build SuperSQL query from matched pattern."""
        
        if pattern_type == "top_n":
            n = match.group(1)
            dimension = self._clean_field_name(match.group(2))
            metric = self._clean_field_name(match.group(3))
            metric_func = self._infer_metric_function(metric)
            
            return template.format(
                s3_path=s3_path,
                metric_func=metric_func,
                metric=metric,
                dimension=dimension,
                limit=n
            )
        
        elif pattern_type == "time_series":
            if len(match.groups()) >= 2:
                metric = self._clean_field_name(match.group(1))
                time_unit = match.group(2) if len(match.groups()) > 1 else "day"
                metric_func = self._infer_metric_function(metric)
                timestamp_field = self._infer_timestamp_field()
                
                return template.format(
                    s3_path=s3_path,
                    metric_func=metric_func,
                    metric=metric,
                    time_unit=time_unit,
                    timestamp_field=timestamp_field
                )
        
        elif pattern_type == "aggregation":
            metric = self._clean_field_name(match.group(1))
            dimension = self._clean_field_name(match.group(2))
            metric_func = self._infer_metric_function_from_query(match.string)
            
            return template.format(
                s3_path=s3_path,
                metric_func=metric_func,
                metric=metric,
                dimension=dimension
            )
        
        elif pattern_type == "counting":
            entity = match.group(1)
            filter_clause, group_by = self._parse_counting_query(entity)
            
            return template.format(
                s3_path=s3_path,
                filter_clause=filter_clause,
                group_by=group_by
            )
        
        elif pattern_type == "filtering":
            # Handle filtering patterns
            if len(match.groups()) >= 3:
                operation = match.group(1)
                context = match.group(2)
                condition = match.group(3)
                filter_condition = self._parse_filter_condition(condition)
                operation_clause = self._parse_operation(operation)
                
                return template.format(
                    s3_path=s3_path,
                    filter_condition=filter_condition,
                    operation=operation_clause
                )
        
        return await self._build_fallback_query(match.string, s3_path, limit)
    
    async def _build_fallback_query(self, query: str, s3_path: str, limit: int) -> str:
        """Build a basic query when no patterns match."""
        logger.warning(f"No pattern matched for query: {query}, using fallback")
        
        # Simple fallback that just returns the first N records
        return f"FROM '{s3_path}' | HEAD {limit}"
    
    def _clean_field_name(self, field: str) -> str:
        """Clean and normalize field names."""
        # Remove common words and clean up
        field = re.sub(r'\b(the|a|an|of|by|for|from|with)\b', '', field).strip()
        # Replace spaces with underscores and make lowercase
        field = re.sub(r'\s+', '_', field.lower())
        # Remove special characters except underscores
        field = re.sub(r'[^a-z0-9_]', '', field)
        return field
    
    def _infer_metric_function(self, metric: str) -> str:
        """Infer the appropriate aggregation function for a metric."""
        metric_lower = metric.lower()
        
        if any(word in metric_lower for word in ['count', 'number', 'total_records']):
            return 'count'
        elif any(word in metric_lower for word in ['revenue', 'sales', 'amount', 'total', 'sum']):
            return 'sum'
        elif any(word in metric_lower for word in ['average', 'avg', 'mean']):
            return 'avg'
        elif any(word in metric_lower for word in ['max', 'maximum', 'highest']):
            return 'max'
        elif any(word in metric_lower for word in ['min', 'minimum', 'lowest']):
            return 'min'
        else:
            return 'sum'  # Default to sum
    
    def _infer_metric_function_from_query(self, query: str) -> str:
        """Infer metric function from the full query text."""
        query_lower = query.lower()
        
        if 'average' in query_lower or 'avg' in query_lower:
            return 'avg'
        elif 'sum' in query_lower or 'total' in query_lower:
            return 'sum'
        elif 'max' in query_lower or 'maximum' in query_lower:
            return 'max'
        elif 'min' in query_lower or 'minimum' in query_lower:
            return 'min'
        else:
            return 'sum'
    
    def _infer_timestamp_field(self) -> str:
        """Infer the most likely timestamp field name."""
        # Common timestamp field names
        return 'timestamp'  # This could be made more sophisticated
    
    def _parse_counting_query(self, entity: str) -> tuple:
        """Parse counting queries to extract filter and grouping information."""
        entity_lower = entity.lower()
        
        # Look for time-based filters
        filter_clause = ""
        group_by = ""
        
        if 'today' in entity_lower:
            today = datetime.now().strftime('%Y-%m-%d')
            filter_clause = f"WHERE date(timestamp) = '{today}' |"
        elif 'yesterday' in entity_lower:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            filter_clause = f"WHERE date(timestamp) = '{yesterday}' |"
        elif 'last 24 hours' in entity_lower:
            filter_clause = f"WHERE timestamp > now() - interval '24 hours' |"
        
        # Look for grouping dimensions
        if 'by' in entity_lower:
            parts = entity_lower.split('by')
            if len(parts) > 1:
                group_field = self._clean_field_name(parts[1].strip())
                group_by = f"BY {group_field}"
        
        return filter_clause, group_by
    
    def _parse_filter_condition(self, condition: str) -> str:
        """Parse natural language filter conditions into SuperSQL."""
        condition_lower = condition.lower().strip()
        
        # Handle common filter patterns
        if 'error' in condition_lower:
            return "status = 'error' OR level = 'error'"
        elif 'success' in condition_lower:
            return "status = 'success'"
        elif 'api' in condition_lower:
            return "service LIKE '%api%'"
        else:
            # Generic condition - might need refinement
            return condition_lower
    
    def _parse_operation(self, operation: str) -> str:
        """Parse the operation part of a query."""
        operation_lower = operation.lower().strip()
        
        if 'count' in operation_lower:
            return "SUMMARIZE count()"
        elif 'show' in operation_lower or 'list' in operation_lower:
            return "HEAD 100"
        else:
            return "SUMMARIZE count()"
    
    async def analyze_data_structure(self, sample_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sample data to determine schema and data quality."""
        if not sample_data or not isinstance(sample_data, list):
            return {
                "schema": {},
                "quality_summary": {"error": "No valid sample data provided"}
            }
        
        schema = {}
        quality_summary = {}
        
        # Analyze first few records to infer schema
        for record in sample_data[:10]:
            if isinstance(record, dict):
                for field, value in record.items():
                    if field not in schema:
                        schema[field] = {
                            "type": self._infer_data_type(value),
                            "sample_values": [],
                            "null_count": 0,
                            "total_count": 0
                        }
                    
                    schema[field]["total_count"] += 1
                    if value is None:
                        schema[field]["null_count"] += 1
                    elif len(schema[field]["sample_values"]) < 3:
                        schema[field]["sample_values"].append(str(value))
        
        # Calculate quality metrics
        for field, info in schema.items():
            quality_summary[field] = {
                "completeness": 1 - (info["null_count"] / max(info["total_count"], 1)),
                "sample_values": info["sample_values"]
            }
        
        return {
            "schema": {field: {"type": info["type"]} for field, info in schema.items()},
            "quality_summary": quality_summary
        }
    
    def _infer_data_type(self, value: Any) -> str:
        """Infer data type from a sample value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            # Try to detect special string types
            if self._looks_like_timestamp(value):
                return "timestamp"
            elif self._looks_like_date(value):
                return "date"
            else:
                return "string"
        elif isinstance(value, (list, tuple)):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "unknown"
    
    def _looks_like_timestamp(self, value: str) -> bool:
        """Check if string looks like a timestamp."""
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
        ]
        return any(re.match(pattern, value) for pattern in timestamp_patterns)
    
    def _looks_like_date(self, value: str) -> bool:
        """Check if string looks like a date."""
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
        ]
        return any(re.match(pattern, value) for pattern in date_patterns)