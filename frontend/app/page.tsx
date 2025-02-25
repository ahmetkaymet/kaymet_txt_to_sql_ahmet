/**
 * Main Page Component
 * 
 * This component serves as the main interface for the natural language to SQL converter.
 * It provides a chat-like interface where users can:
 * - Enter natural language queries
 * - View SQL translations and results
 * - Browse query history by sessions
 * - See detailed explanations of query processing
 * 
 * The component manages:
 * - Real-time query processing
 * - Session management
 * - Error handling
 * - Query history display
 * - Automatic scrolling
 */

'use client'

import React from 'react'
import { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Flex,
  Input,
  Button,
  Stack,
  Text,
  useToast,
  UnorderedList,
  ListItem,
  VStack,
  HStack,
  Heading,
} from '@chakra-ui/react'
import axios from 'axios'
import ClientOnly from './components/ClientOnly'

/**
 * Represents the result of a query execution
 */
interface QueryResult {
  /** Detailed explanation of how the query was processed */
  explanation: string
  /** Generated SQL query */
  sql_query: string
  /** Query execution results */
  results: any[]
  /** Session identifier */
  session_id: string
}

/**
 * Represents a single query in the history
 */
interface QueryHistoryItem {
  /** Unique identifier for the query */
  id: number
  /** Session this query belongs to */
  session_id: string
  /** Original natural language query */
  natural_query: string
  /** Generated SQL query */
  sql_query: string
  /** GPT's explanation of the query processing */
  gpt_explanation: string
  /** Query results (can be string or parsed JSON) */
  query_result: any
  /** When the query was executed */
  timestamp: string
  /** Optional title for the query */
  title: string
}

/**
 * Represents a query session
 */
interface Session {
  /** Unique session identifier */
  id: string
  /** List of queries in this session */
  queries: QueryHistoryItem[]
}

// Configure axios defaults
axios.defaults.baseURL = 'http://localhost:8000';
axios.defaults.timeout = 30000; // 30 seconds timeout
axios.defaults.headers.common['Content-Type'] = 'application/json';
axios.defaults.withCredentials = true;

/**
 * Home component - Main application interface
 * 
 * @returns React component
 */
export default function Home() {
  // State management
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentResult, setCurrentResult] = useState<QueryResult | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const toast = useToast()
  const messagesEndRef = React.useRef<HTMLDivElement>(null)

  /**
   * Scrolls the chat view to the bottom
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  // Auto-scroll when sessions or selected session changes
  useEffect(() => {
    scrollToBottom()
  }, [sessions, selectedSession])

  /**
   * Fetches all query sessions from the server
   */
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const response = await axios.get('/sessions');

        if (!Array.isArray(response.data)) {
          throw new Error('Expected array of sessions but got: ' + typeof response.data);
        }

        const sessionsData = response.data.map((session: Session) => {
          if (!Array.isArray(session.queries)) {
            throw new Error(`Session ${session.id} has no queries array`);
          }

          return {
            ...session,
            queries: session.queries.map((query: QueryHistoryItem) => {
              try {
                // Ensure query has all required fields
                if (!query.title) {
                  query.title = ''; // Set default empty title if missing
                }
                
                return {
                  ...query,
                  query_result: typeof query.query_result === 'string' 
                    ? JSON.parse(query.query_result) 
                    : query.query_result
                };
              } catch (parseError) {
                console.error('Error parsing query:', parseError);
                return query; // Return original query if parsing fails
              }
            })
          };
        });

        setSessions(sessionsData);
        if (sessionsData.length > 0) {
          setSelectedSession(sessionsData[0].id);
        }
      } catch (error) {
        let errorMessage = 'Failed to fetch sessions';
        
        if (axios.isAxiosError(error)) {
          if (error.code === 'ECONNREFUSED') {
            errorMessage = 'Cannot connect to server. Please make sure the backend is running.';
          } else if (error.response) {
            errorMessage = `Server error: ${error.response.status} - ${error.response.statusText}`;
          } else if (error.request) {
            errorMessage = 'No response from server. Please check your connection.';
          } else {
            errorMessage = `Error: ${error.message}`;
          }
        } else if (error instanceof Error) {
          errorMessage = error.message;
        }

        toast({
          title: 'Error',
          description: errorMessage,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    };

    fetchSessions();
  }, [toast]);

  /**
   * Handles query submission
   * - Validates input
   * - Sends query to server
   * - Updates UI with results
   * - Manages error states
   */
  const handleSubmit = async () => {
    if (!query.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter a query',
        status: 'error',
        duration: 3000,
        isClosable: true,
      })
      return
    }

    setLoading(true)
    try {
      const response = await axios.post('/execute-sql', {
        query: query.trim(),
        session_id: selectedSession || undefined
      })
      
      const result = response.data
      setCurrentResult(result)

      // Fetch all sessions to get the latest data
      const sessionsResponse = await axios.get('/sessions')
      const sessionsData = sessionsResponse.data.map((session: Session) => ({
        ...session,
        queries: session.queries.map((query: QueryHistoryItem) => ({
          ...query,
          query_result: typeof query.query_result === 'string' 
            ? JSON.parse(query.query_result) 
            : query.query_result
        }))
      }))

      setSessions(sessionsData)
      setSelectedSession(result.session_id)
      setQuery('')
    } catch (error) {
      let errorMessage = 'Failed to execute query'
      
      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNREFUSED') {
          errorMessage = 'Cannot connect to server. Please make sure the backend is running.'
        } else if (error.response) {
          errorMessage = `Server error: ${error.response.status} - ${error.response.statusText}`
        } else if (error.request) {
          errorMessage = 'No response from server. Please check your connection.'
        } else {
          errorMessage = `Error: ${error.message}`
        }
      }

      toast({
        title: 'Error',
        description: errorMessage,
        status: 'error',
        duration: 3000,
        isClosable: true,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <ClientOnly>
      <Container maxW="container.xl" py={8}>
        <Flex gap={6} h="calc(100vh - 4rem)">
          {/* Sessions Sidebar */}
          <Box w="300px" bg="gray.50" p={4} borderRadius="md" overflowY="auto">
            <Heading size="md" mb={4}>Query History</Heading>
            <VStack spacing={3} align="stretch">
              {sessions.map((session) => (
                <Box
                  key={session.id}
                  p={3}
                  bg={selectedSession === session.id ? "blue.100" : "white"}
                  borderRadius="md"
                  shadow="sm"
                  cursor="pointer"
                  onClick={() => setSelectedSession(session.id)}
                  _hover={{ bg: selectedSession === session.id ? "blue.100" : "gray.100" }}
                >
                  <Text fontSize="sm" color="gray.600">
                    {session.queries && session.queries.length > 0 && session.queries[0].title
                      ? session.queries[0].title
                      : `Session ${session.id}`}
                  </Text>
                  <Text fontSize="xs" color="gray.500">
                    {session.queries?.length || 0} queries
                  </Text>
                </Box>
              ))}
            </VStack>
          </Box>

          {/* Chat Area */}
          <Stack flex={1} spacing={4}>
            {/* Messages Display */}
            <Box flex={1} bg="gray.50" p={4} borderRadius="md" overflowY="auto">
              <VStack spacing={4} align="stretch">
                {selectedSession && sessions.find(s => s.id === selectedSession)?.queries && (
                  [...sessions
                    .find(s => s.id === selectedSession)!
                    .queries].reverse().map((item, index) => (
                      <VStack key={index} spacing={4} align="stretch">
                        {/* User Query */}
                        <HStack justify="flex-end">
                          <Box
                            maxW="70%"
                            bg="blue.500"
                            color="white"
                            p={3}
                            borderRadius="lg"
                          >
                            <Text>{item.natural_query}</Text>
                          </Box>
                        </HStack>

                        {/* System Response */}
                        <HStack justify="flex-start">
                          <Box
                            maxW="70%"
                            bg="white"
                            p={3}
                            borderRadius="lg"
                            shadow="sm"
                          >
                            <VStack align="stretch" spacing={3}>
                              <Text fontWeight="bold">SQL Query:</Text>
                              <Box
                                bg="gray.50"
                                p={2}
                                borderRadius="md"
                                fontFamily="mono"
                              >
                                <Text>{item.sql_query}</Text>
                              </Box>

                              <Text fontWeight="bold">Explanation:</Text>
                              <Text>{item.gpt_explanation}</Text>

                              <Text fontWeight="bold">Results:</Text>
                              {Array.isArray(item.query_result) ? (
                                <UnorderedList>
                                  {item.query_result.map((result, idx) => (
                                    <ListItem key={idx}>
                                      {JSON.stringify(result)}
                                    </ListItem>
                                  ))}
                                </UnorderedList>
                              ) : (
                                <Text>{JSON.stringify(item.query_result)}</Text>
                              )}
                            </VStack>
                          </Box>
                        </HStack>
                      </VStack>
                    ))
                )}
                <div ref={messagesEndRef} />
              </VStack>
            </Box>

            {/* Input Area */}
            <HStack spacing={4}>
              <Input
                flex={1}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your query in natural language..."
                onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
                disabled={loading}
              />
              <Button
                colorScheme="blue"
                onClick={handleSubmit}
                isLoading={loading}
                loadingText="Processing..."
              >
                Send
              </Button>
            </HStack>
          </Stack>
        </Flex>
      </Container>
    </ClientOnly>
  )
} 