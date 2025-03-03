import { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Input,
  Button,
  Text,
  Heading,
  useToast,
  Code,
  Divider,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Stack,
  HStack,
  VStack,
  Badge,
} from '@chakra-ui/react'
import axios from 'axios'

interface QueryResult {
  natural_query: string
  sql_query: string
  explanation: string
  results: any[]
  session_id: string
  title: string
  timestamp: string
}

interface HistoryItem {
  id: string
  queries: QueryResult[]
}

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResult | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const toast = useToast()

  const fetchHistory = async () => {
    setLoadingHistory(true)
    try {
      const response = await axios.get('/sessions')
      setHistory(response.data)
    } catch (error) {
      console.error('Error fetching history:', error)
    } finally {
      setLoadingHistory(false)
    }
  }

  useEffect(() => {
    fetchHistory()
    // Her 30 saniyede bir geçmişi güncelle
    const interval = setInterval(fetchHistory, 30000)
    return () => clearInterval(interval)
  }, [])

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
        session_id: result?.session_id 
      })
      console.log('Backend response:', response.data)
      setResult(response.data)
      setQuery('')
      fetchHistory() // Yeni sorgu sonrası geçmişi güncelle
    } catch (error: any) {
      console.error('Error details:', error.response?.data || error)
      toast({
        title: 'Error',
        description: 'An error occurred while executing the query',
        status: 'error',
        duration: 3000,
        isClosable: true,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box minH="100vh" bg="gray.50" py={8}>
      <Container maxW="container.xl">
        <HStack align="start" spacing={8}>
          {/* History Sidebar */}
          <Box w="300px" bg="white" p={4} rounded="xl" shadow="sm" position="sticky" top={8}>
            <VStack align="stretch" spacing={4}>
              <Heading size="md">Query History</Heading>
              <Divider />
              {loadingHistory ? (
                <Box textAlign="center" py={4}>
                  <Spinner size="sm" />
                  <Text mt={2}>Loading...</Text>
                </Box>
              ) : history.length > 0 ? (
                history.flatMap(session => 
                  session.queries.map((item, index) => (
                    <Box
                      key={`${session.id}-${index}`}
                      p={3}
                      bg={result?.session_id === item.session_id ? 'blue.50' : 'gray.50'}
                      rounded="md"
                      cursor="pointer"
                      onClick={() => setResult(item)}
                      _hover={{ bg: 'blue.50' }}
                    >
                      <Text fontSize="sm" fontWeight="medium" noOfLines={2}>
                        {item.natural_query}
                      </Text>
                      <HStack mt={2} spacing={2}>
                        <Badge colorScheme="blue" fontSize="xs">
                          {new Date(item.timestamp).toLocaleString()}
                        </Badge>
                      </HStack>
                    </Box>
                  ))
                )
              ) : (
                <Text color="gray.500" textAlign="center">No query history yet</Text>
              )}
            </VStack>
          </Box>

          {/* Main Content */}
          <Stack flex={1} spacing={8}>
            {/* Header */}
            <Box textAlign="center">
              <Heading size="xl" mb={2}>Natural Language to SQL Converter</Heading>
              <Text color="gray.600">
                Write your query in natural language, we'll convert it to SQL
              </Text>
            </Box>

            {/* Query Input */}
            <Box w="full" p={6} bg="white" rounded="xl" shadow="sm">
              <Stack spacing={4} direction="column">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Enter your query here..."
                  size="lg"
                  onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
                />
                <Button
                  colorScheme="blue"
                  size="lg"
                  isLoading={loading}
                  onClick={handleSubmit}
                  w="full"
                >
                  Execute Query
                </Button>
              </Stack>
            </Box>

            {/* Results */}
            {loading && (
              <Box textAlign="center">
                <Spinner size="xl" />
                <Text mt={4}>Processing your query...</Text>
              </Box>
            )}

            {result && !loading && (
              <Box w="full" p={6} bg="white" rounded="xl" shadow="sm">
                <Stack spacing={6} direction="column" align="stretch">
                  {/* Original Query */}
                  <Box>
                    <Text fontWeight="bold" mb={2}>Original Query:</Text>
                    <Text fontSize="lg" color="gray.700">{result.natural_query}</Text>
                  </Box>

                  <Divider />

                  {/* SQL Translation */}
                  <Box>
                    <Text fontWeight="bold" mb={2}>SQL Query:</Text>
                    <Code p={4} rounded="md" display="block" whiteSpace="pre-wrap">
                      {result.sql_query}
                    </Code>
                  </Box>

                  <Divider />

                  {/* Explanation */}
                  <Box>
                    <Text fontWeight="bold" mb={2}>Explanation:</Text>
                    <Text p={4} bg="gray.50" rounded="md">
                      {result.explanation}
                    </Text>
                  </Box>

                  <Divider />

                  {/* Query Results */}
                  <Box>
                    <Text fontWeight="bold" mb={4}>Query Results:</Text>
                    {result.results && result.results.length > 0 ? (
                      <Box overflowX="auto">
                        <Table variant="simple">
                          <Thead>
                            <Tr>
                              {Object.keys(result.results[0]).map((key) => (
                                <Th key={key}>{key}</Th>
                              ))}
                            </Tr>
                          </Thead>
                          <Tbody>
                            {result.results.map((row, i) => (
                              <Tr key={i}>
                                {Object.values(row).map((value, j) => (
                                  <Td key={j}>
                                    {typeof value === 'object'
                                      ? JSON.stringify(value)
                                      : String(value)}
                                  </Td>
                                ))}
                              </Tr>
                            ))}
                          </Tbody>
                        </Table>
                      </Box>
                    ) : (
                      <Text color="gray.500">No results found</Text>
                    )}
                  </Box>

                  {/* Session Info */}
                  <HStack spacing={2} fontSize="sm" color="gray.500">
                    <Text>Session ID:</Text>
                    <Code fontSize="xs">{result.session_id}</Code>
                  </HStack>
                </Stack>
              </Box>
            )}
          </Stack>
        </HStack>
      </Container>
    </Box>
  )
}

export default App 