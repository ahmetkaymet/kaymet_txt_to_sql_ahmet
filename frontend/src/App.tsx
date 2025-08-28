import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  chart_generating?: boolean
}

interface ChatStep {
  type: 'explanation' | 'sql' | 'results' | 'chart'
  content: any
  status: 'loading' | 'complete' | 'error'
  timestamp: Date
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
  
  const [error, setError] = useState<string | null>(null)
  const { isOpen, onOpen, onClose } = useDisclosure()
  const toast = useToast()
  
  // Live streaming chat states
  const [chatSteps, setChatSteps] = useState<ChatStep[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentStep, setCurrentStep] = useState<ChatStep | null>(null)
  
  // Responsive sidebar state
  const isDesktop = useBreakpointValue({ base: false, lg: true });
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // Debug: Monitor result state changes
  useEffect(() => {
    console.log('Result state changed:', result);
    console.log('Chart data in result:', result?.chart_data);
    console.log('Chart config in result:', result?.chart_config);
  }, [result]);
  
  // Duplicate API çağrılarını önlemek için useRef ve debouncing
  const isFetching = useRef(false);
  const lastFetchTime = useRef(0);
  const FETCH_COOLDOWN = 2000; // 2 saniye bekleme süresi
  const fetchQueue = useRef<Array<() => void>>([]);

  const fetchHistory = async () => {
    const now = Date.now();
    
    // Eğer zaten fetch yapılıyorsa, yeni çağrıyı queue'ya ekle
    if (isFetching.current) {
      console.log('Fetch in progress, queuing request');
      return new Promise<void>((resolve) => {
        fetchQueue.current.push(resolve);
      });
    }
    
    // Eğer çok kısa süre önce fetch yapıldıysa, yeni çağrı yapma
    if ((now - lastFetchTime.current) < FETCH_COOLDOWN) {
      console.log('Fetch skipped - cooldown active, last fetch was', Math.round((now - lastFetchTime.current) / 1000), 'seconds ago');
      return;
    }
    
    isFetching.current = true;
    lastFetchTime.current = now;
    
    console.log('Fetching history...', new Date().toISOString());
    
    setLoadingHistory(true)
    try {
      // Direkt API_URL kullan
      const response = await axios.get(`${API_URL}/sessions`);
      setHistory(response.data)
      console.log('History fetched successfully');
    } catch (error) {
      console.error('Error fetching history:', error)
    } finally {
      setLoadingHistory(false)
      isFetching.current = false
      
      // Queue'daki bekleyen request'leri işle
      if (fetchQueue.current.length > 0) {
        const nextRequest = fetchQueue.current.shift();
        if (nextRequest) {
          console.log('Processing queued request');
          nextRequest();
        }
      }
    }
  }

  useEffect(() => {
    fetchHistory()
    // Her 5 dakikada bir geçmişi güncelle (daha az sıklıkta)
    const interval = setInterval(fetchHistory, 300000)
    return () => clearInterval(interval)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) return;
    
    // Prevent duplicate API calls
    if (isFetching.current) {
      console.log('Request already in progress, skipping...');
      return;
    }
    
    const startTime = Date.now();
    console.log(`🚀 Starting query: "${query.trim()}" at ${new Date().toISOString()}`);
    
    setIsStreaming(true);
    setLoading(true); // Add loading state
    // Clear previous chat steps and stop any ongoing typing
    setChatSteps([]);
    setResult(null);
    setActiveTab(0);
    
    try {
      isFetching.current = true;
      
      const apiStartTime = Date.now();
      console.log('📡 API call starting...');
      
      const response = await axios.post(`${API_URL}/check-and-execute`, {
        query: query.trim(),
        session_id: result?.session_id
      });
      
      const apiEndTime = Date.now();
      const apiDuration = apiEndTime - apiStartTime;
      console.log(`✅ API response received in ${apiDuration}ms`);
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
        setIsStreaming(false);
        return;
      }
      
      // Check-and-execute response içindeki data nesnesini (ExecuteSQLResponse) almalıyız
      const resultData = response.data.data;
      console.log('Full response:', response.data);
      console.log('Result data:', resultData);
      console.log('Result data type:', typeof resultData);
      console.log('Result data keys:', resultData ? Object.keys(resultData) : 'No data');
      console.log('Chart data from backend:', resultData?.chart_data);
      console.log('Chart config from backend:', resultData?.chart_config);
      
      // Ensure all required fields are present
      const processedResult = {
        natural_query: resultData?.natural_query || '',
        sql_query: resultData?.sql_query || '',
        explanation: resultData?.explanation || '',
        results: resultData?.results || [],
        session_id: resultData?.session_id || '',
        title: resultData?.title || '',
        timestamp: resultData?.timestamp || new Date().toISOString(),
        chart_data: resultData?.chart_data || undefined,
        chart_config: resultData?.chart_config || {}
      };
      
      console.log('Processed result:', processedResult);
      console.log('Processed chart_data:', processedResult.chart_data);
      console.log('Processed chart_config:', processedResult.chart_config);
      
      setResult(processedResult);
      console.log('Result state set to:', processedResult);
      console.log('Result state after set:', result); // This will show old value due to React state updates
      setQuery('');

      // Update chat steps with live streaming effect
      const streamingStartTime = Date.now();
      console.log('🎬 Starting chat streaming...');
      await streamChatSteps(processedResult);
      const streamingEndTime = Date.now();
      const streamingDuration = streamingEndTime - streamingStartTime;
      console.log(`🎭 Chat streaming completed in ${streamingDuration}ms`);

      const totalTime = Date.now() - startTime;
      console.log(`🎉 Total query execution time: ${totalTime}ms`);
      console.log(`📊 Breakdown: API: ${apiDuration}ms, Streaming: ${streamingDuration}ms, Total: ${totalTime}ms`);
      
      // Show success message
      toast({
        title: 'Query Executed Successfully',
        description: `Found ${processedResult.results.length} results in ${totalTime}ms (API: ${apiDuration}ms, UI: ${streamingDuration}ms)`,
        status: 'success',
        duration: 5000,
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
      setIsStreaming(false);
      setLoading(false); // Reset loading state
      isFetching.current = false;
    }
  }

  const streamChatSteps = async (queryResult: QueryResult) => {
    // Clear any existing steps
    setChatSteps([])
    
    // Add explanation step immediately
    setChatSteps(prev => [...prev, {
      type: 'explanation',
      content: queryResult.explanation,
      status: 'complete',
      timestamp: new Date()
    }])

    // Wait a bit for smooth transition
    await new Promise(resolve => setTimeout(resolve, 400))

    // Add SQL step
    setChatSteps(prev => [...prev, {
      type: 'sql',
      content: queryResult.sql_query,
      status: 'complete',
      timestamp: new Date()
    }])

    await new Promise(resolve => setTimeout(resolve, 400))

    // Add results step
    setChatSteps(prev => [...prev, {
      type: 'results',
      content: queryResult.results,
      status: 'complete',
      timestamp: new Date()
    }])

    await new Promise(resolve => setTimeout(resolve, 400))

    // Add chart step if available
    if (queryResult.chart_data && queryResult.chart_data !== 'undefined') {
      setChatSteps(prev => [...prev, {
        type: 'chart',
        content: { 
          chart_data: queryResult.chart_data, 
          chart_config: queryResult.chart_config 
        },
        status: 'complete',
        timestamp: new Date()
      }])
    }
  }





  const generateChart = useCallback(async () => {
    if (!result) return;
    
    // Show loading state
    setResult(prev => prev ? { ...prev, chart_generating: true } : null);
    
    try {
      // Re-run the query to get fresh chart data
      const response = await axios.post(`${API_URL}/check-and-execute`, {
        query: result.natural_query,
        username: "user",
        session_id: result.session_id
      });
      
      if (response.data.status === "success" && response.data.data) {
        const newResult = response.data.data;
        setResult(prev => prev ? {
          ...prev,
          chart_data: newResult.chart_data,
          chart_config: newResult.chart_config,
          chart_generating: false
        } : null);
        
        toast({
          title: "Chart Generated",
          description: "Chart generated successfully",
          status: "success",
          duration: 3000,
          isClosable: true,
        });
      } else {
        setResult(prev => prev ? { ...prev, chart_generating: false } : null);
        toast({
          title: "Chart Generation Failed",
          description: response.data.message || "Failed to generate chart",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (error) {
      console.error('Error generating chart:', error);
      setResult(prev => prev ? { ...prev, chart_generating: false } : null);
      toast({
        title: "Error",
        description: "Failed to generate chart",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  }, [result]);

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
    console.log('renderChart called with result:', result);
    console.log('chart_data:', result?.chart_data);
    console.log('chart_data type:', typeof result?.chart_data);
    console.log('chart_data starts with data:image/:', result?.chart_data?.startsWith('data:image/'));
    
    if (!result?.chart_data) {
      console.log('No chart_data available');
      return (
        <Box textAlign="center" py={8}>
          <Text color="gray.500" mb={4}>No chart available for this data</Text>
          <Button 
            colorScheme="blue" 
            onClick={generateChart}
            leftIcon={<ViewIcon />}
            isLoading={result?.chart_generating}
            loadingText="Generating..."
          >
            Generate Chart
          </Button>
        </Box>
      );
    }

    // Check if it's a base64 image or JSON data
    if (result.chart_data.startsWith('data:image/')) {
      console.log('Rendering PNG image chart');
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
      console.log('Rendering JSON data chart');
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
                    Ask me anything about your HR data
                  </Text>
                  <Text fontSize="sm" color="gray.600">
                    Describe what you want to know about your HR data in natural language
                  </Text>
                </VStack>
                
                {/* HR Quick Query Examples */}
                <Box>
                  <Text fontSize="sm" fontWeight="medium" color="gray.700" mb={3}>
                    Quick HR Analytics:
                  </Text>
                  <HStack spacing={2} wrap="wrap">
                    <Button
                      size="sm"
                      variant="outline"
                      colorScheme="blue"
                      onClick={() => setQuery("Show me employee count by department")}
                    >
                      Employee Count by Dept
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      colorScheme="green"
                      onClick={() => setQuery("What is the average salary by position?")}
                    >
                      Salary by Position
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      colorScheme="purple"
                      onClick={() => setQuery("Analyze employee engagement scores by department")}
                    >
                      Engagement Analysis
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      colorScheme="orange"
                      onClick={() => setQuery("Show me training completion rates")}
                    >
                      Training Metrics
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      colorScheme="teal"
                      onClick={() => setQuery("What is the employee turnover rate by department?")}
                    >
                      Turnover Analysis
                    </Button>
                  </HStack>
                </Box>
                
                <HStack spacing={4} as="form" onSubmit={handleSubmit}>
                  <Input
                    placeholder="e.g., Show me employee count by department, Find average salary by position, Analyze engagement scores..."
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
                    onKeyPress={(e) => e.key === 'Enter' && handleSubmit(e)}
                  />
                  <Button
                    type="submit"
                    colorScheme="blue"
                    size="lg"
                    px={8}
                    py={6}
                    fontSize="lg"
                    fontWeight="bold"
                    borderRadius="xl"
                    boxShadow="0 4px 20px rgba(102, 126, 234, 0.3)"
                    isLoading={loading}
                    loadingText="Executing..."
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

          {/* Error Display */}
          {error && (
            <Box
              bg="red.50"
              borderRadius="2xl"
              p={6}
              border="1px"
              borderColor="red.200"
              mb={6}
            >
              <Alert status="error" borderRadius="xl">
                <AlertIcon />
                <Box>
                  <AlertTitle>Error!</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Box>
              </Alert>
            </Box>
          )}

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



          {/* Live Streaming Chat Steps */}
          {isStreaming && chatSteps.length > 0 && (
            <Box
              bg="white"
              borderRadius="2xl"
              overflow="hidden"
              boxShadow="0 4px 20px rgba(0, 0, 0, 0.08)"
              border="1px"
              borderColor="gray.100"
              mb={6}
            >
              <Box 
                bg="blue.50" 
                px={8} 
                py={6} 
                borderBottom="1px" 
                borderColor="blue.200"
              >
                <HStack spacing={3} align="center">
                  <Spinner size="sm" color="blue.500" />
                  <Text fontSize="lg" fontWeight="bold" color="blue.800">
                    AI Analizi Canlı Olarak Oluşturuluyor...
                  </Text>
                </HStack>
              </Box>
              
              <Box p={8}>
                <VStack spacing={6} align="stretch">
                  {chatSteps.map((step, index) => (
                    <Box
                      key={index}
                      p={6}
                      bg={step.status === 'loading' ? 'gray.50' : 'white'}
                      borderRadius="xl"
                      border="1px"
                      borderColor={step.status === 'loading' ? 'gray.200' : 'blue.200'}
                      transition="all 0.3s ease"
                      _hover={{ transform: 'translateY(-2px)', boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)' }}
                    >
                      <HStack justify="space-between" mb={4}>
                        <Badge 
                          colorScheme={step.status === 'loading' ? 'gray' : 'blue'} 
                          fontSize="sm" 
                          borderRadius="full" 
                          px={3} 
                          py={1}
                        >
                          {step.type === 'explanation' && 'AI Açıklaması'}
                          {step.type === 'sql' && 'SQL Sorgusu'}
                          {step.type === 'results' && 'Veri Sonuçları'}
                          {step.type === 'chart' && 'Görselleştirme'}
                        </Badge>
                        {step.status === 'loading' && (
                          <Spinner size="sm" color="blue.500" />
                        )}
                        {step.status === 'complete' && (
                          <Icon as={CheckIcon} color="green.500" />
                        )}
                      </HStack>
                      
                      {step.type === 'explanation' && (
                        <Box>
                          <Text fontSize="lg" fontWeight="semibold" color="gray.800" mb={3}>
                            AI Analizi
                          </Text>
                          <Box
                            bg="blue.50"
                            p={4}
                            borderRadius="lg"
                            border="1px"
                            borderColor="blue.200"
                          >
                            <Text color="gray.700">
                              {step.content}
                            </Text>
                          </Box>
                        </Box>
                      )}
                      
                      {step.type === 'sql' && (
                        <Box>
                          <Text fontSize="lg" fontWeight="semibold" color="gray.800" mb={3}>
                            SQL Sorgusu
                          </Text>
                          <Box
                            bg="gray.900"
                            p={4}
                            borderRadius="lg"
                            overflow="auto"
                          >
                            <Code color="green.400" fontSize="sm">
                              {step.content}
                            </Code>
                          </Box>
                        </Box>
                      )}
                      
                      {step.type === 'results' && (
                        <Box>
                          <Text fontSize="lg" fontWeight="semibold" color="gray.800" mb={3}>
                            Veri Sonuçları ({step.content.length} satır)
                          </Text>
                          <Box
                            bg="gray.50"
                            p={4}
                            borderRadius="lg"
                            border="1px"
                            borderColor="gray.200"
                            maxH="300px"
                            overflow="auto"
                          >
                            <Table variant="simple" size="sm">
                              <Thead>
                                <Tr>
                                  {Object.keys(step.content[0] || {}).map(key => (
                                    <Th key={key}>{key}</Th>
                                  ))}
                                </Tr>
                              </Thead>
                              <Tbody>
                                {step.content.slice(0, 10).map((row: any, idx: number) => (
                                  <Tr key={idx}>
                                    {Object.values(row).map((value: any, valIdx: number) => (
                                      <Td key={valIdx}>{String(value)}</Td>
                                    ))}
                                  </Tr>
                                ))}
                              </Tbody>
                            </Table>
                            {step.content.length > 10 && (
                              <Text fontSize="sm" color="gray.600" mt={2} textAlign="center">
                                ... ve {step.content.length - 10} satır daha
                              </Text>
                            )}
                          </Box>
                        </Box>
                      )}
                      
                      {step.type === 'chart' && (
                        <Box>
                          <Text fontSize="lg" fontWeight="semibold" color="gray.800" mb={3}>
                            Görselleştirme
                          </Text>
                          <Box
                            bg="white"
                            p={4}
                            borderRadius="lg"
                            border="1px"
                            borderColor="gray.200"
                          >
                            {step.content.chart_data && step.content.chart_data.startsWith('data:image/') ? (
                              <Image 
                                src={step.content.chart_data} 
                                alt="Data Chart"
                                w="full"
                                h="auto"
                                borderRadius="md"
                              />
                            ) : step.content.chart_data ? (
                              <Text color="gray.600">Chart formatında görüntülenemiyor</Text>
                            ) : (
                              <Text color="gray.600">Chart henüz oluşturulmadı</Text>
                            )}
                          </Box>
                        </Box>
                      )}
                    </Box>
                  ))}
                </VStack>
              </Box>
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
                          {result.results ? result.results.length : 0} results
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
                              <Text color="gray.700">{result.natural_query || 'No query available'}</Text>
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
                            {result.explanation || 'No explanation available'}
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
                            {result.sql_query || 'No SQL query available'}
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
                              {result.results ? result.results.length : 0} rows returned
                            </Text>
                          </HStack>
                      
                          {result.results && result.results.length > 0 ? (
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
                                {Object.keys(result.results[0] || {}).map((key) => (
                                  <Th key={key} py={4} px={6} color="gray.700" fontWeight="semibold">
                                    {key}
                                  </Th>
                                ))}
                              </Tr>
                            </Thead>
                            <Tbody>
                              {result.results.map((row, index) => (
                                <Tr key={index} _hover={{ bg: "gray.50" }}>
                                  {Object.values(row || {}).map((value, cellIndex) => (
                                    <Td key={cellIndex} py={3} px={6} color="gray.800">
                                      {String(value || '')}
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