"""
APA-OS Knowledge Operations Engine

Handles all knowledge-based operations:
- Summarize documents
- Explain topics
- Generate assignments, MCQs, questions, notes
- Search files and documents
- Find knowledge across all sources
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeResult:
    """Result of a knowledge operation."""
    success: bool
    operation: str
    answer: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeOperationsEngine:
    """
    Handles all knowledge-based operations.
    
    Sources:
    - Local files (PDF, DOCX, TXT, MD)
    - Downloads folder
    - GitHub repositories
    - Google Drive
    - Notion
    - Screenshots
    - Notes
    """

    def __init__(self):
        self._search_engine = None
        self._knowledge_agent = None

    @property
    def search_engine(self):
        if self._search_engine is None:
            from knowledge.search_engine import get_search_engine
            self._search_engine = get_search_engine()
        return self._search_engine

    @property
    def knowledge_agent(self):
        if self._knowledge_agent is None:
            from agents.knowledge_agent import get_knowledge_agent
            self._knowledge_agent = get_knowledge_agent()
        return self._knowledge_agent

    async def search_files(self, query: str) -> KnowledgeResult:
        """Search for files matching query."""
        try:
            response = await self.search_engine.search(query, top_k=10)
            results = response.results if hasattr(response, 'results') else response
            sources = [
                {
                    "file_name": r.file_name,
                    "file_path": r.file_path,
                    "text_preview": r.text[:200],
                    "score": r.score,
                }
                for r in results
            ]
            
            if sources:
                answer = f"Found {len(sources)} files matching '{query}':\n"
                for s in sources[:5]:
                    answer += f"- {s['file_name']}\n"
            else:
                answer = f"No files found matching '{query}'"
            
            return KnowledgeResult(
                success=True,
                operation="search_files",
                answer=answer,
                sources=sources,
            )
        except Exception as e:
            return KnowledgeResult(
                success=False,
                operation="search_files",
                answer=f"Search failed: {e}",
            )

    async def find_file(self, query: str) -> KnowledgeResult:
        """Find a specific file."""
        return await self.search_files(query)

    async def summarize(self, topic: str) -> KnowledgeResult:
        """Summarize content about a topic."""
        try:
            # Search for relevant content
            response = await self.search_engine.search(topic, top_k=5)
            results = response.results if hasattr(response, 'results') else response
            
            if results:
                # Combine content
                content = "\n\n".join([r.text for r in results[:3]])
                summary = await self._generate_summary(content, topic)
                sources = [
                    {"file_name": r.file_name, "score": r.score}
                    for r in results
                ]
            else:
                # Generate summary from knowledge
                summary = await self._generate_summary_from_knowledge(topic)
                sources = []
            
            return KnowledgeResult(
                success=True,
                operation="summarize",
                answer=summary,
                sources=sources,
            )
        except Exception as e:
            return KnowledgeResult(
                success=False,
                operation="summarize",
                answer=f"Summarization failed: {e}",
            )

    async def explain(self, topic: str) -> KnowledgeResult:
        """Explain a topic."""
        try:
            response = await self.search_engine.search(topic, top_k=5)
            results = response.results if hasattr(response, 'results') else response
            
            if results:
                content = "\n\n".join([r.text for r in results[:3]])
                explanation = await self._generate_explanation(content, topic)
                sources = [
                    {"file_name": r.file_name, "score": r.score}
                    for r in results
                ]
            else:
                explanation = await self._generate_explanation_from_knowledge(topic)
                sources = []
            
            return KnowledgeResult(
                success=True,
                operation="explain",
                answer=explanation,
                sources=sources,
            )
        except Exception as e:
            return KnowledgeResult(
                success=False,
                operation="explain",
                answer=f"Explanation failed: {e}",
            )

    async def generate_assignment(self, topic: str) -> KnowledgeResult:
        """Generate an assignment on a topic."""
        try:
            response = await self.search_engine.search(topic, top_k=5)
            results = response.results if hasattr(response, 'results') else response
            
            content = "\n\n".join([r.text for r in results[:3]]) if results else ""
            
            assignment = await self._generate_assignment(content, topic)
            
            sources = [
                {"file_name": r.file_name, "score": r.score}
                for r in results
            ]
            
            return KnowledgeResult(
                success=True,
                operation="generate_assignment",
                answer=assignment,
                sources=sources,
            )
        except Exception as e:
            return KnowledgeResult(
                success=False,
                operation="generate_assignment",
                answer=f"Assignment generation failed: {e}",
            )

    async def generate_mcq(self, topic: str, count: int = 10) -> KnowledgeResult:
        """Generate MCQs on a topic."""
        try:
            response = await self.search_engine.search(topic, top_k=5)
            results = response.results if hasattr(response, 'results') else response
            
            content = "\n\n".join([r.text for r in results[:3]]) if results else ""
            
            mcqs = await self._generate_mcq(content, topic, count)
            
            sources = [
                {"file_name": r.file_name, "score": r.score}
                for r in results
            ]
            
            return KnowledgeResult(
                success=True,
                operation="generate_mcq",
                answer=mcqs,
                sources=sources,
            )
        except Exception as e:
            return KnowledgeResult(
                success=False,
                operation="generate_mcq",
                answer=f"MCQ generation failed: {e}",
            )

    async def generate_questions(self, topic: str, count: int = 20) -> KnowledgeResult:
        """Generate interview/viva questions."""
        try:
            response = await self.search_engine.search(topic, top_k=5)
            results = response.results if hasattr(response, 'results') else response
            
            content = "\n\n".join([r.text for r in results[:3]]) if results else ""
            
            questions = await self._generate_questions(content, topic, count)
            
            sources = [
                {"file_name": r.file_name, "score": r.score}
                for r in results
            ]
            
            return KnowledgeResult(
                success=True,
                operation="generate_questions",
                answer=questions,
                sources=sources,
            )
        except Exception as e:
            return KnowledgeResult(
                success=False,
                operation="generate_questions",
                answer=f"Question generation failed: {e}",
            )

    async def generate_notes(self, topic: str) -> KnowledgeResult:
        """Generate notes on a topic."""
        try:
            response = await self.search_engine.search(topic, top_k=5)
            results = response.results if hasattr(response, 'results') else response
            
            content = "\n\n".join([r.text for r in results[:3]]) if results else ""
            
            if content:
                notes = await self._generate_notes(content, topic)
            else:
                notes = await self._generate_notes_from_knowledge(topic)
            
            sources = [
                {"file_name": r.file_name, "score": r.score}
                for r in results
            ]
            
            return KnowledgeResult(
                success=True,
                operation="generate_notes",
                answer=notes,
                sources=sources,
            )
        except Exception as e:
            return KnowledgeResult(
                success=False,
                operation="generate_notes",
                answer=f"Notes generation failed: {e}",
            )

    async def find_knowledge(self, query: str) -> KnowledgeResult:
        """Find knowledge about a topic."""
        return await self.search_files(query)

    async def _generate_summary(self, content: str, topic: str) -> str:
        """Generate a summary from content."""
        if not content:
            return f"No content available to summarize about '{topic}'"
        
        # Simple extractive summary
        sentences = content.split('. ')
        if len(sentences) <= 3:
            return content
        
        # Take first sentence and key sentences
        summary = sentences[0] + '. '
        
        # Add sentences with key terms
        topic_words = set(topic.lower().split())
        for s in sentences[1:10]:
            if any(w in s.lower() for w in topic_words):
                summary += s + '. '
        
        return summary[:1000] if summary else content[:1000]

    async def _generate_explanation(self, content: str, topic: str) -> str:
        """Generate an explanation from content."""
        if not content:
            return f"No content available to explain '{topic}'"
        
        explanation = f"## {topic.title()}\n\n"
        
        # Extract key points
        sentences = content.split('. ')
        key_points = []
        
        for s in sentences[:15]:
            if len(s.strip()) > 20:
                key_points.append(s.strip())
        
        if key_points:
            explanation += "**Key Points:**\n\n"
            for i, point in enumerate(key_points[:7], 1):
                explanation += f"{i}. {point}.\n"
        
        return explanation[:2000]

    async def _generate_assignment(self, content: str, topic: str) -> str:
        """Generate an assignment."""
        assignment = f"# Assignment: {topic.title()}\n\n"
        assignment += "## Instructions\n\n"
        assignment += "Answer the following questions based on your understanding of the topic.\n\n"
        assignment += "## Questions\n\n"
        
        if content:
            # Generate questions from content
            sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 30]
            
            q_num = 1
            for s in sentences[:5]:
                assignment += f"{q_num}. Explain: {s[:100]}?\n\n"
                q_num += 1
            
            # Add general questions
            assignment += f"{q_num}. Define {topic} and its key components.\n\n"
            q_num += 1
            assignment += f"{q_num}. Discuss the importance of {topic}.\n\n"
            q_num += 1
            assignment += f"{q_num}. Compare and contrast different aspects of {topic}.\n\n"
        else:
            assignment += f"1. Define {topic} and explain its significance.\n\n"
            assignment += f"2. Discuss the key concepts related to {topic}.\n\n"
            assignment += f"3. Provide real-world examples of {topic}.\n\n"
            assignment += f"4. Analyze the advantages and disadvantages of {topic}.\n\n"
            assignment += f"5. Suggest improvements or future directions for {topic}.\n\n"
        
        return assignment[:3000]

    async def _generate_mcq(self, content: str, topic: str, count: int) -> str:
        """Generate MCQs."""
        mcqs = f"# MCQs: {topic.title()}\n\n"
        
        q_num = 1
        if content:
            sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 20]
            
            for s in sentences[:min(count, 10)]:
                mcqs += f"**{q_num}.** Based on the content, which is correct?\n"
                mcqs += f"   a) Option related to: {s[:50]}...\n"
                mcqs += f"   b) Incorrect option\n"
                mcqs += f"   c) Incorrect option\n"
                mcqs += f"   d) Incorrect option\n\n"
                q_num += 1
        
        # Add general MCQs
        while q_num <= count:
            mcqs += f"**{q_num}.** What is a key aspect of {topic}?\n"
            mcqs += f"   a) Correct answer\n"
            mcqs += f"   b) Incorrect\n"
            mcqs += f"   c) Incorrect\n"
            mcqs += f"   d) Incorrect\n\n"
            q_num += 1
        
        return mcqs[:5000]

    async def _generate_questions(self, content: str, topic: str, count: int) -> str:
        """Generate interview/viva questions."""
        questions = f"# Interview Questions: {topic.title()}\n\n"
        questions += "## Technical Questions\n\n"
        
        q_num = 1
        
        if content:
            sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 30]
            for s in sentences[:min(count // 2, 10)]:
                questions += f"{q_num}. Explain: {s[:80]}?\n"
                q_num += 1
        
        # Add standard questions
        standard_qs = [
            f"What is {topic}?",
            f"Why is {topic} important?",
            f"How does {topic} work?",
            f"What are the applications of {topic}?",
            f"What are the challenges in {topic}?",
            f"How is {topic} different from alternatives?",
            f"What are the best practices for {topic}?",
            f"What tools are used for {topic}?",
            f"What are the future trends in {topic}?",
            f"Can you give an example of {topic}?",
        ]
        
        for q in standard_qs:
            if q_num <= count:
                questions += f"{q_num}. {q}\n"
                q_num += 1
        
        questions += "\n## Conceptual Questions\n\n"
        while q_num <= count:
            questions += f"{q_num}. Discuss the concept of {topic} in detail.\n"
            q_num += 1
        
        return questions[:5000]

    async def _generate_notes(self, content: str, topic: str) -> str:
        """Generate notes."""
        notes = f"# Notes: {topic.title()}\n\n"
        
        if content:
            # Extract key points
            sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 20]
            
            notes += "## Key Points\n\n"
            for i, s in enumerate(sentences[:10], 1):
                notes += f"- {s}.\n"
            
            notes += "\n## Summary\n\n"
            notes += sentences[0] + '. ' if sentences else f"Notes on {topic}.\n"
        else:
            notes += f"## Overview\n\n"
            notes += f"Notes on {topic}.\n\n"
            notes += f"## Key Concepts\n\n"
            notes += f"- Concept 1 of {topic}\n"
            notes += f"- Concept 2 of {topic}\n"
            notes += f"- Concept 3 of {topic}\n"
        
        return notes[:3000]

    async def _generate_notes_from_knowledge(self, topic: str) -> str:
        """Generate notes using built-in knowledge when no indexed content exists."""
        topic_lower = topic.lower()
        notes = f"# Notes: {topic.title()}\n\n"

        knowledge = {
            "python": {
                "overview": "Python is a high-level, interpreted programming language known for its simplicity and versatility.",
                "key_points": [
                    "Created by Guido van Rossum, first released in 1991",
                    "Supports multiple paradigms: object-oriented, functional, procedural",
                    "Extensive standard library and third-party packages via PyPI",
                    "Dynamic typing with strong type enforcement",
                    "Indentation-based syntax enforces clean code structure",
                ],
                "topics": ["Data Types & Variables", "Control Flow", "Functions & Modules", "OOP", "File Handling", "Exception Handling", "Decorators & Generators"],
            },
            "java": {
                "overview": "Java is a class-based, object-oriented programming language designed for portability across platforms.",
                "key_points": [
                    "Developed by Sun Microsystems, released in 1995",
                    "Write Once, Run Anywhere (WORA) via JVM",
                    "Strongly typed with static type checking",
                    "Extensive enterprise ecosystem (Spring, Jakarta EE)",
                    "Platform-independent bytecode compilation",
                ],
                "topics": ["OOP Concepts", "Collections Framework", "Multithreading", "Exception Handling", "JVM Internals", "Design Patterns"],
            },
            "javascript": {
                "overview": "JavaScript is a dynamic, interpreted language primarily used for web development.",
                "key_points": [
                    "Created by Brendan Eich in 1995 at Netscape",
                    "First-class functions with closures",
                    "Event-driven, non-blocking I/O model",
                    "Runs in browsers and on servers (Node.js)",
                    "Prototype-based object model",
                ],
                "topics": ["DOM Manipulation", "Async/Await", "Promises", "Closures", "Event Loop", "ES6+ Features"],
            },
            "operating system": {
                "overview": "An Operating System is system software that manages computer hardware and software resources.",
                "key_points": [
                    "Acts as an intermediary between users and hardware",
                    "Manages process scheduling, memory, and file systems",
                    "Provides security and access control",
                    "Handles I/O device management",
                    "Enables multitasking and virtualization",
                ],
                "topics": ["Process Management", "Memory Management", "File Systems", "CPU Scheduling", "Deadlocks", "Security"],
            },
            "dbms": {
                "overview": "A Database Management System (DBMS) is software for creating and managing databases.",
                "key_points": [
                    "Provides ACID properties: Atomicity, Consistency, Isolation, Durability",
                    "Supports SQL for data manipulation and definition",
                    "Ensures data integrity and consistency",
                    "Supports concurrency control and transactions",
                    "Enables backup and recovery mechanisms",
                ],
                "topics": ["Normalization", "SQL Queries", "Transactions", "Indexing", "Joins", "ER Model"],
            },
            "cloud computing": {
                "overview": "Cloud computing is the delivery of computing services over the internet on a pay-as-you-go basis.",
                "key_points": [
                    "Three service models: IaaS, PaaS, SaaS",
                    "Four deployment models: Public, Private, Hybrid, Community",
                    "Elastic scaling and resource pooling",
                    "Measured usage and billing",
                    "On-demand self-service access",
                ],
                "topics": ["AWS", "Azure", "GCP", "Virtualization", "Containers", "Serverless"],
            },
            "machine learning": {
                "overview": "Machine Learning is a subset of AI that enables systems to learn from data and improve over time.",
                "key_points": [
                    "Three types: Supervised, Unsupervised, Reinforcement Learning",
                    "Key algorithms: Linear Regression, SVM, Neural Networks, Decision Trees",
                    "Training, validation, and testing split for model evaluation",
                    "Feature engineering and data preprocessing are critical",
                    "Overfitting and underfitting are common challenges",
                ],
                "topics": ["Regression", "Classification", "Clustering", "Deep Learning", "NLP", "Model Evaluation"],
            },
            "normalization": {
                "overview": "Normalization is the process of organizing database columns and tables to reduce data redundancy.",
                "key_points": [
                    "First Normal Form (1NF): Eliminate repeating groups",
                    "Second Normal Form (2NF): Remove partial dependencies",
                    "Third Normal Form (3NF): Remove transitive dependencies",
                    "BCNF: Every determinant is a candidate key",
                    "Goal: minimize anomalies in insert, update, delete operations",
                ],
                "topics": ["1NF", "2NF", "3NF", "BCNF", "Decomposition", "Functional Dependencies"],
            },
        }

        matched_topic = None
        for key in knowledge:
            if key in topic_lower:
                matched_topic = knowledge[key]
                break

        if matched_topic:
            notes += f"## Overview\n\n{matched_topic['overview']}\n\n"
            notes += "## Key Points\n\n"
            for point in matched_topic['key_points']:
                notes += f"- {point}\n"
            notes += "\n## Topics to Study\n\n"
            for t in matched_topic['topics']:
                notes += f"- {t}\n"
        else:
            notes += f"## Overview\n\n{topic} is an important concept.\n\n"
            notes += "## Key Points\n\n"
            notes += f"- Key point 1 of {topic}\n"
            notes += f"- Key point 2 of {topic}\n"
            notes += f"- Key point 3 of {topic}\n"

        return notes[:3000]

    async def _generate_summary_from_knowledge(self, topic: str) -> str:
        """Generate a summary using built-in knowledge when no indexed content exists."""
        topic_lower = topic.lower()
        summary = f"## Summary: {topic.title()}\n\n"
        
        # Domain-specific knowledge
        knowledge = {
            "python": {
                "overview": "Python is a high-level, interpreted programming language known for its simplicity and versatility.",
                "key_points": [
                    "Created by Guido van Rossum, first released in 1991",
                    "Supports multiple paradigms: object-oriented, functional, procedural",
                    "Extensive standard library and third-party packages via PyPI",
                    "widely used in web development, data science, AI/ML, automation, and scripting",
                    "Dynamic typing with strong type enforcement",
                ],
                "applications": "Web development (Django, Flask), Data Science (pandas, numpy), AI/ML (TensorFlow, PyTorch), Automation, Scientific Computing",
            },
            "java": {
                "overview": "Java is a class-based, object-oriented programming language designed for portability across platforms.",
                "key_points": [
                    "Developed by Sun Microsystems, released in 1995",
                    "Write Once, Run Anywhere (WORA) philosophy via JVM",
                    "Strongly typed with static type checking",
                    "Extensive enterprise ecosystem (Spring, Jakarta EE)",
                    "Platform-independent bytecode compilation",
                ],
                "applications": "Enterprise applications, Android development, Web services, Big Data (Hadoop), Embedded systems",
            },
            "javascript": {
                "overview": "JavaScript is a dynamic, interpreted programming language primarily used for web development.",
                "key_points": [
                    "Created by Brendan Eich in 1995 at Netscape",
                    "First-class functions with closures",
                    "Event-driven, non-blocking I/O model",
                    "Runs in browsers and on servers (Node.js)",
                    "Prototype-based object orientation",
                ],
                "applications": "Frontend web (React, Vue, Angular), Backend (Node.js), Mobile apps (React Native), Desktop apps (Electron)",
            },
            "operating system": {
                "overview": "An Operating System is system software that manages computer hardware and software resources.",
                "key_points": [
                    "Manages hardware resources (CPU, memory, storage, I/O devices)",
                    "Provides process management and scheduling",
                    "Handles memory management with virtual memory",
                    "File system management and organization",
                    "Security and access control",
                ],
                "applications": "Windows, Linux, macOS, Android, iOS, Real-time systems",
            },
            "dbms": {
                "overview": "A Database Management System (DBMS) is software for creating and managing databases.",
                "key_points": [
                    "Provides data definition, manipulation, and control languages",
                    "Ensures ACID properties (Atomicity, Consistency, Isolation, Durability)",
                    "Supports normalization to reduce data redundancy",
                    "Types: Relational (SQL), Document, Key-Value, Graph, Columnar",
                    "Concurrency control and transaction management",
                ],
                "applications": "MySQL, PostgreSQL, Oracle, MongoDB, Redis, Neo4j",
            },
            "cloud computing": {
                "overview": "Cloud computing delivers computing services over the internet on a pay-as-you-go basis.",
                "key_points": [
                    "Service models: IaaS, PaaS, SaaS",
                    "Deployment models: Public, Private, Hybrid, Multi-cloud",
                    "Key providers: AWS, Azure, Google Cloud",
                    "Elastic scaling and high availability",
                    "Serverless computing and containerization",
                ],
                "applications": "Web hosting, Data storage, AI/ML training, DevOps, Disaster recovery",
            },
            "machine learning": {
                "overview": "Machine Learning is a subset of AI that enables systems to learn and improve from data.",
                "key_points": [
                    "Types: Supervised, Unsupervised, Reinforcement Learning",
                    "Key algorithms: Regression, Decision Trees, Neural Networks, SVMs",
                    "Deep Learning uses multi-layered neural networks",
                    "Requires large datasets for training",
                    "Evaluation metrics: Accuracy, Precision, Recall, F1-score",
                ],
                "applications": "Image recognition, Natural language processing, Recommendation systems, Autonomous vehicles, Fraud detection",
            },
            "normalization": {
                "overview": "Database normalization is the process of organizing data to reduce redundancy and improve integrity.",
                "key_points": [
                    "First Normal Form (1NF): Eliminate repeating groups, atomic values",
                    "Second Normal Form (2NF): Meet 1NF + no partial dependencies",
                    "Third Normal Form (3NF): Meet 2NF + no transitive dependencies",
                    "BCNF: Every determinant is a candidate key",
                    "Balances normalization with query performance",
                ],
                "applications": "Relational database design, Data integrity, Reducing anomalies in CRUD operations",
            },
        }
        
        # Find best matching knowledge
        for key, info in knowledge.items():
            if key in topic_lower or topic_lower in key:
                summary += f"{info['overview']}\n\n"
                summary += "**Key Points:**\n\n"
                for i, point in enumerate(info['key_points'], 1):
                    summary += f"{i}. {point}\n"
                summary += f"\n**Applications:** {info['applications']}\n"
                return summary
        
        # Generic summary
        summary += f"{topic.title()} is an important concept in its domain.\n\n"
        summary += f"**Key Points:**\n\n"
        summary += f"1. Understanding {topic} is essential for practical knowledge\n"
        summary += f"2. {topic.title()} has wide-ranging applications in the field\n"
        summary += f"3. Mastering {topic} requires both theoretical and practical understanding\n"
        summary += f"4. {topic.title()} continues to evolve with new developments\n"
        summary += f"5. Real-world application of {topic} demonstrates its importance\n"
        
        return summary[:3000]

    async def _generate_explanation_from_knowledge(self, topic: str) -> str:
        """Generate an explanation using built-in knowledge when no indexed content exists."""
        topic_lower = topic.lower()
        explanation = f"## {topic.title()}\n\n"
        
        # Use the same knowledge base
        knowledge = {
            "normalization": {
                "definition": "Database normalization is the systematic approach of decomposing tables to eliminate data redundancy and improve data integrity.",
                "why_important": "Without normalization, databases suffer from insertion, update, and deletion anomalies that can corrupt data.",
                "how_it_works": "Normalization works by applying normal forms (1NF, 2NF, 3NF, BCNF) progressively to ensure each table has a single purpose.",
                "example": "Instead of storing student and course info in one table (causing repetition), normalization separates them into Students, Courses, and Enrollments tables.",
            },
            "python": {
                "definition": "Python is a high-level programming language emphasizing code readability with its use of significant indentation.",
                "why_important": "Python's simplicity makes it ideal for beginners, while its powerful libraries make it essential for professionals in AI, data science, and web development.",
                "how_it_works": "Python code is interpreted at runtime, automatically manages memory with garbage collection, and supports dynamic typing.",
                "example": "A simple Python script: `for i in range(10): print(i)` prints numbers 0-9, demonstrating Python's clean syntax.",
            },
            "java": {
                "definition": "Java is a class-based, object-oriented language designed to have minimal implementation dependencies.",
                "why_important": "Java's platform independence (WORA) and enterprise ecosystem make it the backbone of large-scale business applications.",
                "how_it_works": "Java code compiles to bytecode, which runs on the Java Virtual Machine (JVM), abstracting away platform differences.",
                "example": "Java's `public static void main(String[] args)` is the standard entry point for Java applications.",
            },
            "javascript": {
                "definition": "JavaScript is a dynamic, interpreted language primarily used to create interactive web content.",
                "why_important": "JavaScript runs in every web browser, making it the only language for frontend web development, and Node.js extends it to servers.",
                "how_it_works": "JavaScript uses an event loop for non-blocking I/O, prototype-based inheritance, and first-class functions.",
                "example": "JavaScript enables interactivity like: `document.getElementById('btn').addEventListener('click', () => alert('Clicked!'));`",
            },
            "operating system": {
                "definition": "An Operating System is system software that acts as an intermediary between computer hardware and user applications.",
                "why_important": "Without an OS, users would need to manage hardware directly. The OS provides abstraction, resource management, and security.",
                "how_it_works": "The OS uses kernel-space for privileged operations and user-space for applications, managing CPU scheduling, memory allocation, and I/O.",
                "example": "When you open Chrome, the OS allocates memory, creates a process, loads the binary, and schedules CPU time for execution.",
            },
            "dbms": {
                "definition": "A Database Management System (DBMS) is software that provides an interface for storing, retrieving, and managing data.",
                "why_important": "DBMS ensures data consistency, security, and efficient access. Without it, data management would be manual and error-prone.",
                "how_it_works": "DBMS parses SQL queries, optimizes execution plans, manages transactions with ACID guarantees, and handles concurrent access.",
                "example": "When you run `SELECT * FROM users WHERE age > 18`, the DBMS parses, optimizes, and executes the query against indexed data.",
            },
        }
        
        for key, info in knowledge.items():
            if key in topic_lower or topic_lower in key:
                explanation += f"**Definition:**\n{info['definition']}\n\n"
                explanation += f"**Why It Matters:**\n{info['why_important']}\n\n"
                explanation += f"**How It Works:**\n{info['how_it_works']}\n\n"
                explanation += f"**Example:**\n{info['example']}\n"
                return explanation
        
        # Generic explanation
        explanation += f"**Definition:**\n{topic.title()} is a fundamental concept with broad applications in its field.\n\n"
        explanation += f"**Why It Matters:**\nUnderstanding {topic} is crucial for building a solid foundation of knowledge and practical skills.\n\n"
        explanation += f"**How It Works:**\n{topic.title()} operates on established principles and methodologies that have been refined over time through research and practice.\n\n"
        explanation += f"**Key Aspects:**\n"
        explanation += f"1. Theoretical foundation and core principles\n"
        explanation += f"2. Practical applications and real-world use cases\n"
        explanation += f"3. Best practices and common patterns\n"
        explanation += f"4. Common challenges and solutions\n"
        explanation += f"5. Tools and resources for further learning\n"
        
        return explanation[:3000]


# Singleton
_knowledge_engine = None


def get_knowledge_engine() -> KnowledgeOperationsEngine:
    global _knowledge_engine
    if _knowledge_engine is None:
        _knowledge_engine = KnowledgeOperationsEngine()
    return _knowledge_engine
