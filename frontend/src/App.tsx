import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Input,
  VStack,
  HStack,
  Text,
  useToast,
  Container,
  Heading,
  Textarea,
  Badge,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  IconButton,
  Image,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Divider,
  Spinner,
  Stack,
  Code,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Icon,
  Flex,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  useDisclosure,
  useBreakpointValue
} from '@chakra-ui/react';
import { ViewIcon, CopyIcon, CheckIcon, HamburgerIcon } from '@chakra-ui/icons';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

// Plotly import with proper typing
declare global {
  interface Window {
    Plotly: any;
  }
}

interface QueryResult {
  natural_query: string
  sql_query: string
  explanation: string
  results: any[]
  session_id: string
  title: string
  timestamp: string
  chart_data?: string
  chart_config?: any
}

interface HistoryItem {
  id: string
  queries: QueryResult[]
}

// API URL'ini doğru şekilde tanımla
const API_URL = 'http://localhost:8000';

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResult | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [activeTab, setActiveTab] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { isOpen, onOpen, onClose } = useDisclosure()
  const toast = useToast()
  
  // Responsive sidebar state
  const isDesktop = useBreakpointValue({ base: false, lg: true });
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const fetchHistory = async () => {
    setLoadingHistory(true)
    try {
      // Direkt API_URL kullan
      const response = await axios.get(`${API_URL}/sessions`);
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
      // Direkt API_URL kullan
      const response = await axios.post(`${API_URL}/check-and-execute`, {
        query: query.trim(),
        session_id: result?.session_id
      });
      console.log('Backend response:', response.data)
      
      // Yanıt no_data durumundaysa
      if (response.data.status === 'no_data') {
        toast({
          title: 'No Data Available',
          description: response.data.message,
          status: 'warning',
          duration: 5000,
          isClosable: true,
        });
        setLoading(false);
        return;
      }
      
      // Check-and-execute response içindeki data nesnesini (ExecuteSQLResponse) almalıyız
      setResult(response.data.data)
      setQuery('')
      fetchHistory()
      
      // Show success message
      toast({
        title: 'Query Executed Successfully',
        description: `Found ${response.data.data.results.length} results`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
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

  const generateChart = async () => {
    if (!result) return;
    
    try {
      const response = await axios.post(`${API_URL}/chart`, {
        query: result.natural_query,
        chart_type: result.chart_config?.chart_type || 'auto',
        x_column: result.chart_config?.x_column,
        y_column: result.chart_config?.y_column
      });
      
      if (response.data.success) {
        setResult(prev => prev ? {
          ...prev,
          chart_data: response.data.chart_data,
          chart_config: response.data.chart_config
        } : null);
        
        toast({
          title: "Chart Generated",
          description: response.data.message,
          status: "success",
          duration: 3000,
          isClosable: true,
        });
      } else {
        toast({
          title: "Chart Generation Failed",
          description: response.data.message,
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (error) {
      console.error('Error generating chart:', error);
      toast({
        title: "Error",
        description: "Failed to generate chart",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const loadQueryFromHistory = (queryData: any) => {
    console.log('Loading query from history:', queryData);
    
    // Backend'den gelen veri yapısına göre düzenle
    let results = [];
    try {
      if (queryData.results) {
        // Yeni format: results alanı direkt geliyor
        results = queryData.results;
      } else if (queryData.query_result) {
        // Eğer query_result olarak geliyorsa (eski format)
        results = JSON.parse(queryData.query_result);
      }
    } catch (error) {
      console.error('Error parsing results:', error);
      results = [];
    }

    let chartConfig = undefined;
    try {
      if (queryData.chart_config) {
        chartConfig = typeof queryData.chart_config === 'string' 
          ? JSON.parse(queryData.chart_config) 
          : queryData.chart_config;
      }
    } catch (error) {
      console.error('Error parsing chart_config:', error);
      chartConfig = undefined;
    }

    const queryResult: QueryResult = {
      natural_query: queryData.natural_query,
      sql_query: queryData.sql_query,
      explanation: queryData.explanation || '',
      results: results,
      session_id: queryData.session_id || '',
      title: queryData.title || queryData.natural_query,
      timestamp: queryData.timestamp || new Date().toISOString(),
      chart_data: queryData.chart_data || undefined,
      chart_config: chartConfig
    };
    
    console.log('Processed query result:', queryResult);
    setResult(queryResult);
    setActiveTab(0); // AI Analysis tab'ına geç
  };

  const renderChart = () => {
    if (!result?.chart_data) {
      return (
        <Box textAlign="center" py={8}>
          <Text color="gray.500" mb={4}>No chart available for this data</Text>
          <Button 
            colorScheme="blue" 
            onClick={generateChart}
            leftIcon={<ViewIcon />}
          >
            Generate Chart
          </Button>
        </Box>
      );
    }

    // Check if it's a base64 image or JSON data
    if (result.chart_data.startsWith('data:image/')) {
      // PNG image chart
      return (
        <Box>
          <HStack justify="space-between" mb={4}>
            <Text fontWeight="bold">Data Visualization</Text>
            <HStack>
              <Text fontSize="sm" color="gray.600">
                Type: {result.chart_config?.chart_type || 'Unknown'}
              </Text>
              <IconButton
                aria-label="Generate new chart"
                icon={<ViewIcon />}
                size="sm"
                onClick={generateChart}
              />
            </HStack>
          </HStack>
          
          <Box 
            border="1px" 
            borderColor="gray.200" 
            borderRadius="md" 
            overflow="hidden"
            bg="white"
          >
            <Image 
              src={result.chart_data} 
              alt="Data Chart"
              w="full"
              h="auto"
              cursor="pointer"
              onClick={onOpen}
              _hover={{ opacity: 0.8 }}
            />
          </Box>
          
          {result.chart_config?.reason && (
            <Text fontSize="sm" color="gray.600" mt={2}>
              {result.chart_config.reason}
            </Text>
          )}
        </Box>
      );
    } else {
      // JSON data (HTML fallback)
      try {
        const chartInfo = JSON.parse(result.chart_data);
        
        return (
          <Box>
            <HStack justify="space-between" mb={4}>
              <Text fontWeight="bold">Data Visualization</Text>
              <HStack>
                <Text fontSize="sm" color="gray.600">
                  Type: {chartInfo.chart_type || 'Unknown'}
                </Text>
                <IconButton
                  aria-label="Generate new chart"
                  icon={<ViewIcon />}
                  size="sm"
                  onClick={generateChart}
                />
              </HStack>
            </HStack>
            
            <Box 
              border="1px" 
              borderColor="gray.200" 
              borderRadius="md" 
              overflow="hidden"
              bg="white"
              p={4}
            >
              <VStack spacing={4} align="stretch">
                <Text fontWeight="bold" fontSize="lg">{chartInfo.title}</Text>
                <Text fontSize="sm" color="gray.600">
                  Data Points: {chartInfo.data_points} | Columns: {chartInfo.columns?.join(', ')}
                </Text>
                
                {chartInfo.fallback && (
                  <Alert status="info">
                    <AlertIcon />
                    <Text fontSize="sm">Using Plotly.js rendering (PNG export failed)</Text>
                  </Alert>
                )}
                
                {/* Chart container for Plotly.js */}
                <Box 
                  id="chart-container"
                  w="full" 
                  h="400px"
                  border="1px dashed"
                  borderColor="gray.300"
                  borderRadius="md"
                  display="flex"
                  alignItems="center"
                  justifyContent="center"
                >
                  <Text color="gray.500">Chart loading...</Text>
                </Box>
              </VStack>
            </Box>
            
            {result.chart_config?.reason && (
              <Text fontSize="sm" color="gray.600" mt={2}>
                {result.chart_config.reason}
              </Text>
            )}
          </Box>
        );
      } catch (error) {
        console.error('Error parsing chart data:', error);
        return (
          <Box textAlign="center" py={8}>
            <Text color="red.500" mb={4}>Error rendering chart</Text>
            <Button 
              colorScheme="blue" 
              onClick={generateChart}
              leftIcon={<ViewIcon />}
            >
              Regenerate Chart
            </Button>
          </Box>
        );
      }
    }
  };

  // Effect to render charts when chart data changes
  useEffect(() => {
    if (result?.chart_data && !result.chart_data.startsWith('data:image/')) {
      try {
        const chartInfo = JSON.parse(result.chart_data);
        if (chartInfo.html && chartInfo.chart_type !== 'table') {
          const chartContainer = document.getElementById('chart-container');
          if (chartContainer && window.Plotly) {
            // Parse the HTML and extract Plotly data
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = chartInfo.html;
            const plotlyDiv = tempDiv.querySelector('.plotly-graph-div') as any;
            
            if (plotlyDiv && plotlyDiv.data) {
              // Clear container and render with Plotly
              chartContainer.innerHTML = '';
              window.Plotly.newPlot(chartContainer, plotlyDiv.data || [], plotlyDiv.layout || {}, {
                responsive: true,
                displayModeBar: true
              });
            }
          }
        }
      } catch (error) {
        console.error('Error rendering chart:', error);
      }
    }
  }, [result?.chart_data]);

  

  return (
    <Box minH="100vh" bg="gray.50">
      {/* Modern Header */}
      <Box 
        borderBottom="1px" 
        borderColor="gray.200" 
        px={6} 
        py={4}
        position="sticky"
        top={0}
        zIndex={10}
        backdropFilter="blur(10px)"
        bg="rgba(255, 255, 255, 0.95)"
      >
        <Container maxW="7xl">
          <HStack justify="space-between" align="center">
            <HStack spacing={3}>
              <Box
                w={8}
                h={8}
                bg="linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
                borderRadius="full"
                display="flex"
                alignItems="center"
                justifyContent="center"
                boxShadow="0 4px 12px rgba(102, 126, 234, 0.4)"
              >
                <Text color="white" fontWeight="bold" fontSize="sm">AI</Text>
              </Box>
              <VStack spacing={0} align="start">
                <Heading size="lg" bg="linear-gradient(135deg, #667eea 0%, #764ba2 100%)" bgClip="text" fontWeight="bold">
                  AImet
                </Heading>
                <Text fontSize="sm" color="gray.600" fontWeight="medium">
                  AI-Powered Data Analytics
                </Text>
              </VStack>
            </HStack>
            
            <HStack spacing={4}>
              {/* Mobile menu button */}
              {!isDesktop && (
                <IconButton
                  aria-label="Open sidebar"
                  icon={<HamburgerIcon />}
                  onClick={() => setSidebarOpen(true)}
                  variant="ghost"
                  size="sm"
                />
              )}
              
              {/* Desktop sidebar toggle */}
              {isDesktop && (
              <Button
                size="sm"
                variant="ghost"
                colorScheme="blue"
                  onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                leftIcon={<Icon as={ViewIcon} />}
              >
                  {sidebarCollapsed ? 'Show History' : 'Hide History'}
                </Button>
              )}
              
              <Button
                size="sm"
                variant="ghost"
                colorScheme="green"
                onClick={() => {
                  console.log('Current history:', history);
                  if (history.length > 0 && history[0].queries.length > 0) {
                    console.log('Testing loadQueryFromHistory with:', history[0].queries[0]);
                    loadQueryFromHistory(history[0].queries[0]);
                  }
                }}
              >
                Test Load
              </Button>
            </HStack>
          </HStack>
        </Container>
      </Box>

      {/* Main Layout with Sidebar */}
      <Flex h="calc(100vh - 80px)">
        {/* Desktop Sidebar */}
        {isDesktop && (
          <Box
            w={sidebarCollapsed ? "60px" : "350px"}
            bg="white"
            borderRight="1px"
            borderColor="gray.200"
            transition="width 0.3s ease"
            overflow="hidden"
            position="relative"
          >
            {sidebarCollapsed ? (
              // Collapsed sidebar
              <VStack spacing={4} py={4} align="center">
                <IconButton
                  aria-label="Expand sidebar"
                  icon={<ViewIcon />}
                  onClick={() => setSidebarCollapsed(false)}
                  variant="ghost"
                  size="sm"
                  colorScheme="blue"
                />
              </VStack>
            ) : (
              // Expanded sidebar
              <VStack spacing={0} align="stretch" h="full">
                {/* Sidebar Header */}
                <Box 
                  bg="gray.50" 
                  px={6} 
                  py={4} 
                  borderBottom="1px" 
                  borderColor="gray.200"
                >
                  <HStack justify="space-between" align="center">
                    <Text fontSize="lg" fontWeight="semibold" color="gray.800">
                      Query History
                    </Text>
                    <IconButton
                      aria-label="Collapse sidebar"
                      icon={<ViewIcon />}
                      onClick={() => setSidebarCollapsed(true)}
                      variant="ghost"
                      size="sm"
                      colorScheme="blue"
                    />
                  </HStack>
                </Box>
                
                {/* History List */}
                <Box flex={1} overflowY="auto" p={4}>
                  {loadingHistory ? (
                    <VStack spacing={4} py={8}>
                      <Spinner size="md" color="blue.500" />
                      <Text fontSize="sm" color="gray.600">Loading history...</Text>
                    </VStack>
                  ) : history.length > 0 ? (
                    <VStack spacing={3} align="stretch">
                      {history.flatMap(session => 
                        session.queries.map((item, index) => (
                          <Box
                            key={`${session.id}-${index}`}
                            p={3}
                            bg={result?.session_id === item.session_id ? 'blue.50' : 'gray.50'}
                            borderRadius="lg"
                            cursor="pointer"
                            onClick={() => {
                              console.log('History item clicked:', item);
                              loadQueryFromHistory(item);
                            }}
                            _hover={{ 
                              bg: result?.session_id === item.session_id ? 'blue.100' : 'gray.100',
                              transform: 'translateY(-1px)',
                              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)'
                            }}
                            transition="all 0.2s"
                            border="1px"
                            borderColor={result?.session_id === item.session_id ? 'blue.200' : 'gray.200'}
                          >
                            <VStack spacing={2} align="start">
                              <Text fontSize="sm" fontWeight="medium" color="gray.800" noOfLines={2}>
                                {item.natural_query}
                              </Text>
                              <HStack spacing={2} justify="space-between" w="full">
                                <Badge colorScheme="blue" fontSize="xs" borderRadius="full" px={2} py={1}>
                                  {new Date(item.timestamp).toLocaleDateString()}
                                </Badge>
                                {item.chart_data && (
                                  <Badge colorScheme="green" fontSize="xs" borderRadius="full" px={2} py={1}>
                                    Chart
                                  </Badge>
                                )}
                              </HStack>
                            </VStack>
                          </Box>
                        ))
                      )}
                    </VStack>
                  ) : (
                    <Box textAlign="center" py={8}>
                      <Text color="gray.500" fontSize="sm">
                        No queries yet
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        Start asking questions to see history
                      </Text>
                    </Box>
                  )}
                </Box>
              </VStack>
            )}
          </Box>
        )}

        {/* Main Content Area */}
        <Box flex={1} overflowY="auto">
          <Container maxW="6xl" py={8}>
        <VStack spacing={8} align="stretch">
          {/* Query Input Section */}
          <Box
            bg="white"
            borderRadius="2xl"
            p={8}
            boxShadow="0 4px 20px rgba(0, 0, 0, 0.08)"
            border="1px"
            borderColor="gray.100"
          >
            <VStack spacing={6} align="stretch">
              <VStack spacing={2} align="start">
                <Text fontSize="lg" fontWeight="semibold" color="gray.800">
                  Ask me anything about your data
                </Text>
                <Text fontSize="sm" color="gray.600">
                  Describe what you want to know in natural language
                </Text>
              </VStack>
              
              <HStack spacing={4}>
                <Input
                  placeholder="e.g., Show me sales by state, Find all stores in New York..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  size="lg"
                  borderRadius="xl"
                  border="2px"
                  borderColor="gray.200"
                  _focus={{
                    borderColor: "blue.400",
                    boxShadow: "0 0 0 3px rgba(66, 153, 225, 0.1)"
                  }}
                  _hover={{ borderColor: "gray.300" }}
                  onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
                />
                <Button
                  colorScheme="blue"
                  size="lg"
                  px={8}
                  borderRadius="xl"
                  onClick={handleSubmit}
                  isLoading={loading}
                  loadingText="Analyzing..."
                  bg="linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
                  _hover={{
                    transform: "translateY(-2px)",
                    boxShadow: "0 8px 25px rgba(102, 126, 234, 0.4)"
                  }}
                  transition="all 0.2s"
                >
                  Execute
                </Button>
              </HStack>
            </VStack>
          </Box>

          {/* Loading State */}
          {loading && (
            <Box
              bg="white"
              borderRadius="2xl"
              p={12}
              textAlign="center"
              boxShadow="0 4px 20px rgba(0, 0, 0, 0.08)"
              border="1px"
              borderColor="gray.100"
            >
              <VStack spacing={6}>
                <Spinner size="xl" color="blue.500" thickness="4px" />
                <VStack spacing={2}>
                  <Text fontSize="xl" fontWeight="semibold" color="gray.800">
                    Analyzing your query with AI
                  </Text>
                  <Text fontSize="sm" color="gray.600">
                    This may take a few moments...
                  </Text>
                </VStack>
              </VStack>
            </Box>
          )}

          {/* Results */}
          {result && (
            <Box
              bg="white"
              borderRadius="2xl"
              overflow="hidden"
              boxShadow="0 4px 20px rgba(0, 0, 0, 0.08)"
              border="1px"
              borderColor="gray.100"
            >
              {/* Result Header */}
              <Box 
                bg="gray.50" 
                px={8} 
                py={6} 
                borderBottom="1px" 
                borderColor="gray.200"
              >
                <VStack spacing={3} align="start">
                      <Text fontSize="xl" fontWeight="bold" color="gray.800">
                        {result.title}
                      </Text>
                      <HStack spacing={4} wrap="wrap">
                        <Badge colorScheme="blue" fontSize="sm" borderRadius="full" px={3} py={1}>
                          {new Date(result.timestamp).toLocaleDateString()}
                        </Badge>
                        {result.chart_data && (
                          <Badge colorScheme="green" fontSize="sm" borderRadius="full" px={3} py={1}>
                            Visualization Available
                          </Badge>
                        )}
                        <Badge colorScheme="purple" fontSize="sm" borderRadius="full" px={3} py={1}>
                          {result.results.length} results
                        </Badge>
                  </HStack>
                </VStack>
              </Box>

                  {/* Result Tabs */}
                  <Tabs index={activeTab} onChange={setActiveTab} colorScheme="blue">
                <TabList bg="gray.50" px={8} pt={4}>
                  <Tab 
                    _selected={{ 
                      color: "blue.600",
                          borderColor: "blue.600",
                      fontWeight: "semibold"
                    }}
                  >
                        AI Analysis
                  </Tab>
                  <Tab 
                    _selected={{ 
                      color: "blue.600",
                          borderColor: "blue.600",
                      fontWeight: "semibold"
                    }}
                  >
                        SQL Query
                  </Tab>
                  <Tab 
                    _selected={{ 
                      color: "blue.600",
                          borderColor: "blue.600",
                      fontWeight: "semibold"
                    }}
                      >
                        Data Results
                      </Tab>
                      <Tab 
                        _selected={{ 
                          color: "blue.600", 
                          borderColor: "blue.600",
                          fontWeight: "semibold"
                        }}
                      >
                        Data Visualization
                  </Tab>
                </TabList>

                <TabPanels>
                      {/* AI Analysis */}
                  <TabPanel p={8}>
                    <VStack spacing={6} align="stretch">
                      <Box>
                        <Text fontSize="lg" fontWeight="semibold" color="gray.800" mb={3}>
                              Natural Language Query
                        </Text>
                        <Box
                          bg="gray.50"
                              p={4}
                              borderRadius="lg"
                          border="1px"
                          borderColor="gray.200"
                            >
                              <Text color="gray.700">{result.natural_query}</Text>
                            </Box>
                          </Box>

                          <Box>
                            <Text fontSize="lg" fontWeight="semibold" color="gray.800" mb={3}>
                              AI Explanation
                            </Text>
                            <Box
                              bg="blue.50"
                              p={4}
                              borderRadius="lg"
                              border="1px"
                              borderColor="blue.200"
                        >
                          <ReactMarkdown
                            components={{
                                  code({node, className, children, ...props}: any) {
                                    const match = /language-(\w+)/.exec(className || '')
                                return match ? (
                                  <SyntaxHighlighter
                                    style={atomDark}
                                    language={match[1]}
                                    PreTag="div"
                                        customStyle={{}}
                                        {...props}
                                  >
                                    {String(children).replace(/\n$/, '')}
                                  </SyntaxHighlighter>
                                ) : (
                                      <code className={className} {...props}>
                                    {children}
                                      </code>
                                    )
                                  }
                            }}
                          >
                            {result.explanation}
                          </ReactMarkdown>
                        </Box>
                      </Box>
                        </VStack>
                      </TabPanel>

                      {/* SQL Query */}
                      <TabPanel p={8}>
                        <VStack spacing={4} align="stretch">
                          <HStack justify="space-between" align="center">
                            <Text fontSize="lg" fontWeight="semibold" color="gray.800">
                              Generated SQL Query
                        </Text>
                            <HStack spacing={2}>
                          <Button
                            size="sm"
                                variant="outline"
                                colorScheme="blue"
                            onClick={() => {
                              navigator.clipboard.writeText(result.sql_query);
                              toast({
                                    title: "SQL copied!",
                                    description: "SQL query copied to clipboard",
                                status: "success",
                                duration: 2000,
                                isClosable: true,
                              });
                            }}
                                leftIcon={<Icon as={CopyIcon} />}
                          >
                                Copy SQL
                          </Button>
                            </HStack>
                          </HStack>
                          
                          <Box
                            bg="gray.900"
                            p={4}
                            borderRadius="lg"
                            overflow="auto"
                            maxH="400px"
                          >
                          <SyntaxHighlighter
                            style={atomDark}
                            language="sql"
                            customStyle={{
                              margin: 0,
                                backgroundColor: 'transparent',
                                fontSize: '14px'
                            }}
                          >
                            {result.sql_query}
                          </SyntaxHighlighter>
                      </Box>
                    </VStack>
                  </TabPanel>

                      {/* Data Results */}
                  <TabPanel p={8}>
                        <VStack spacing={4} align="stretch">
                          <HStack justify="space-between" align="center">
                      <Text fontSize="lg" fontWeight="semibold" color="gray.800">
                        Query Results
                      </Text>
                            <Text fontSize="sm" color="gray.600">
                              {result.results.length} rows returned
                            </Text>
                          </HStack>
                      
                          {result.results.length > 0 ? (
                        <Box
                              overflow="auto"
                              maxH="500px"
                          border="1px"
                          borderColor="gray.200"
                              borderRadius="lg"
                        >
                          <Table variant="simple" bg="white">
                            <Thead bg="gray.100">
                              <Tr>
                                {Object.keys(result.results[0]).map((key) => (
                                  <Th key={key} py={4} px={6} color="gray.700" fontWeight="semibold">
                                    {key}
                                  </Th>
                                ))}
                              </Tr>
                            </Thead>
                            <Tbody>
                              {result.results.map((row, index) => (
                                <Tr key={index} _hover={{ bg: "gray.50" }}>
                                  {Object.values(row).map((value, cellIndex) => (
                                    <Td key={cellIndex} py={3} px={6} color="gray.800">
                                      {String(value)}
                                    </Td>
                                  ))}
                                </Tr>
                              ))}
                            </Tbody>
                          </Table>
                        </Box>
                      ) : (
                        <Box textAlign="center" py={12}>
                          <Text color="gray.500" fontSize="lg">
                            No results found for this query
                          </Text>
                        </Box>
                      )}
                    </VStack>
                  </TabPanel>

                  {/* Data Visualization */}
                  <TabPanel p={8}>
                    {renderChart()}
                  </TabPanel>
                </TabPanels>
              </Tabs>
            </Box>
          )}
            </VStack>
          </Container>
              </Box>
      </Flex>

      {/* Mobile Sidebar Drawer */}
      <Drawer
        isOpen={sidebarOpen}
        placement="left"
        onClose={() => setSidebarOpen(false)}
        size="xs"
      >
        <DrawerOverlay />
        <DrawerContent>
          <DrawerCloseButton />
          <DrawerHeader bg="gray.50" borderBottom="1px" borderColor="gray.200">
            Query History
          </DrawerHeader>
          <DrawerBody p={4}>
            {loadingHistory ? (
              <VStack spacing={4} py={8}>
                <Spinner size="md" color="blue.500" />
                <Text fontSize="sm" color="gray.600">Loading history...</Text>
              </VStack>
            ) : history.length > 0 ? (
              <VStack spacing={3} align="stretch">
                  {history.flatMap(session => 
                    session.queries.map((item, index) => (
                      <Box
                        key={`${session.id}-${index}`}
                      p={3}
                        bg={result?.session_id === item.session_id ? 'blue.50' : 'gray.50'}
                      borderRadius="lg"
                        cursor="pointer"
                      onClick={() => {
                        console.log('History item clicked:', item);
                        loadQueryFromHistory(item);
                        setSidebarOpen(false); // Close drawer after selection
                      }}
                        _hover={{ 
                          bg: result?.session_id === item.session_id ? 'blue.100' : 'gray.100',
                        transform: 'translateY(-1px)',
                        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)'
                        }}
                        transition="all 0.2s"
                        border="1px"
                        borderColor={result?.session_id === item.session_id ? 'blue.200' : 'gray.200'}
                      >
                      <VStack spacing={2} align="start">
                        <Text fontSize="sm" fontWeight="medium" color="gray.800" noOfLines={2}>
                            {item.natural_query}
                          </Text>
                        <HStack spacing={2} justify="space-between" w="full">
                          <Badge colorScheme="blue" fontSize="xs" borderRadius="full" px={2} py={1}>
                                {new Date(item.timestamp).toLocaleDateString()}
                              </Badge>
                              {item.chart_data && (
                            <Badge colorScheme="green" fontSize="xs" borderRadius="full" px={2} py={1}>
                                  Chart
                                </Badge>
                              )}
                          </HStack>
                        </VStack>
                      </Box>
                    ))
                  )}
                </VStack>
            ) : (
              <Box textAlign="center" py={8}>
                <Text color="gray.500" fontSize="sm">
                  No queries yet
                </Text>
                <Text color="gray.400" fontSize="xs">
                  Start asking questions to see history
                </Text>
            </Box>
          )}
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      {/* Chart Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="6xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Data Visualization</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            {result?.chart_data && (
              <Image 
                src={result.chart_data} 
                alt="Data Chart" 
                w="full" 
                h="auto"
              />
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </Box>
  )
}

export default App 