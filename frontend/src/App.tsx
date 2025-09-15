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
  IconButton,
  Image,
  Alert,
  AlertIcon,
  Spinner,
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
import { ViewIcon, CopyIcon, CheckIcon, HamburgerIcon, AddIcon, DeleteIcon, ArrowUpIcon } from '@chakra-ui/icons';
import axios from 'axios';

// Plotly import with proper typing
declare global {
  interface Window {
    Plotly: any;
  }
}

interface QueryResult {
  id?: string
  natural_query: string
  user_query?: string // Kullanıcının orijinal sorusu
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

// Utility function to format timestamp to Turkey time
const formatTimestampToTurkeyTime = (timestamp: string): string => {
  try {
    console.log('Raw timestamp received:', timestamp);
    const date = new Date(timestamp);
    console.log('Parsed date:', date);
    console.log('Date ISO string:', date.toISOString());
    console.log('Date local string:', date.toString());
    
    // Alternative approach: Add 3 hours manually if timestamp is in UTC
    // This is more reliable than timezone conversion
    const turkeyTime = new Date(date.getTime() + (3 * 60 * 60 * 1000));
    console.log('Turkey time (manual +3h):', turkeyTime);
    
    const formattedTime = turkeyTime.toLocaleTimeString('tr-TR', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false
    });
    
    console.log('Formatted time (Turkey):', formattedTime);
    return formattedTime;
  } catch (error) {
    console.error('Error formatting timestamp:', error);
    return '--:--';
  }
};

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResult | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  const { isOpen, onClose } = useDisclosure()
  const toast = useToast()
  
  // Live streaming chat states
  const [chatSteps, setChatSteps] = useState<ChatStep[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  
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

  const handleNewChat = () => {
    setResult(null);
    setChatSteps([]);
    setQuery('');
    setIsStreaming(false);
    setLoading(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) return;
    
    // Prevent duplicate API calls
    if (isFetching.current) {
      console.log('Request already in progress, skipping...');
      return;
    }
    
    const startTime = Date.now();
    const endpoint = 'crew-ai-execute'; // Her zaman CrewAI kullan
    console.log(`🚀 Starting query: "${query.trim()}" with ${endpoint} at ${new Date().toISOString()}`);
    
    setIsStreaming(true);
    setLoading(true); // Add loading state
    // Clear previous chat steps and stop any ongoing typing
    setChatSteps([]);
    setResult(null);
    
    try {
      isFetching.current = true;
      
      const apiStartTime = Date.now();
      console.log('📡 API call starting...');
      
      const response = await axios.post(`${API_URL}/${endpoint}`, {
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
          title: 'Veri Bulunamadı',
          description: response.data.message,
          status: 'warning',
          duration: 5000,
          isClosable: true,
        });
        setIsStreaming(false);
        return;
      }
      
      // CrewAI endpoint'i direkt ExecuteSQLResponse döndürür
      const resultData = response.data;
      console.log('Full response:', response.data);
      console.log('Result data:', resultData);
      console.log('Result data type:', typeof resultData);
      console.log('Result data keys:', resultData ? Object.keys(resultData) : 'No data');
      console.log('Chart data from backend:', resultData?.chart_data);
      console.log('Chart config from backend:', resultData?.chart_config);
      console.log('Chart data type:', typeof resultData?.chart_data);
      console.log('Chart data length:', resultData?.chart_data?.length);
      console.log('Chart data starts with data:image:', resultData?.chart_data?.startsWith('data:image/'));
      
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
      
      // Kullanıcının sorusunu da result'a ekle
      const resultWithUserQuery = {
        ...processedResult,
        user_query: query.trim() // Kullanıcının sorusunu ekle
      };
      
      setResult(resultWithUserQuery);
      console.log('Result state set to:', resultWithUserQuery);
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
        title: 'Sorgu Başarıyla Çalıştırıldı',
        description: `${processedResult.results.length} sonuç ${totalTime}ms içinde bulundu (API: ${apiDuration}ms, UI: ${streamingDuration}ms)`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
    } catch (error: any) {
      console.error('Error details:', error.response?.data || error)
      toast({
        title: 'Hata',
        description: 'Sorgu çalıştırılırken bir hata oluştu',
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
    console.log('=== CHART STEP DEBUG ===');
    console.log('queryResult.chart_data:', queryResult.chart_data);
    console.log('queryResult.chart_data type:', typeof queryResult.chart_data);
    console.log('queryResult.chart_data !== undefined:', queryResult.chart_data !== 'undefined');
    console.log('queryResult.chart_data !== null:', queryResult.chart_data !== null);
    console.log('Should add chart step:', queryResult.chart_data && queryResult.chart_data !== 'undefined' && queryResult.chart_data !== null);
    
    if (queryResult.chart_data && queryResult.chart_data !== 'undefined' && queryResult.chart_data !== null) {
      console.log('Adding chart step to chat steps');
      setChatSteps(prev => [...prev, {
        type: 'chart',
        content: { 
          chart_data: queryResult.chart_data, 
          chart_config: queryResult.chart_config 
        },
        status: 'complete',
        timestamp: new Date()
      }])
    } else {
      console.log('NOT adding chart step - conditions not met');
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
          title: "Grafik Oluşturuldu",
          description: "Grafik başarıyla oluşturuldu",
          status: "success",
          duration: 3000,
          isClosable: true,
        });
      } else {
        setResult(prev => prev ? { ...prev, chart_generating: false } : null);
        toast({
          title: "Grafik Oluşturulamadı",
          description: response.data.message || "Grafik oluşturulamadı",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (error) {
      console.error('Error generating chart:', error);
      setResult(prev => prev ? { ...prev, chart_generating: false } : null);
      toast({
        title: "Hata",
        description: "Grafik oluşturulamadı",
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
  };

  const renderChart = () => {
    console.log('=== RENDER CHART DEBUG ===');
    console.log('renderChart called with result:', result);
    console.log('chart_data:', result?.chart_data);
    console.log('chart_data type:', typeof result?.chart_data);
    console.log('chart_data starts with data:image/:', result?.chart_data?.startsWith('data:image/'));
    console.log('chart_data length:', result?.chart_data?.length);
    console.log('chart_config:', result?.chart_config);
    
    if (!result?.chart_data || result.chart_data === 'undefined' || result.chart_data === null) {
      console.log('No chart_data available');
      return (
        <Box textAlign="center" py={8}>
          <Text color="gray.500" mb={4}>Bu veri için grafik mevcut değil</Text>
          <Button 
            colorScheme="gray" 
            onClick={generateChart}
            leftIcon={<ViewIcon />}
            isLoading={result?.chart_generating}
            loadingText="Oluşturuluyor..."
          >
            Grafik Oluştur
          </Button>
        </Box>
      );
    }

    // Check if it's a base64 image or JSON data
    if (result.chart_data.startsWith('data:image/')) {
      console.log('✅ Rendering PNG image chart');
      console.log('Chart data length:', result.chart_data.length);
      console.log('Chart data type:', result.chart_data.substring(0, 50) + '...');
      // PNG image chart
      return (
        <Box>
          <HStack justify="space-between" mb={4}>
            <Text fontWeight="bold">Veri Görselleştirme</Text>
            <HStack>
              <Text fontSize="sm" color="gray.600">
                Tip: {result.chart_config?.chart_type || 'Bilinmiyor'}
              </Text>
              <IconButton
                aria-label="Yeni grafik oluştur"
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
              width="100%"
              height="400px"
              objectFit="contain"
              cursor="pointer"
              onClick={() => {
                // Open in new tab
                window.open(result.chart_data, '_blank');
              }}
              _hover={{ opacity: 0.8 }}
              onError={(e) => {
                console.error('Image load error:', e);
                console.error('Chart data length:', result.chart_data?.length);
                console.error('Chart data starts with:', result.chart_data?.substring(0, 100));
              }}
              onLoad={() => {
                console.log('✅ Image loaded successfully');
              }}
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
              <Text fontWeight="bold">Veri Görselleştirme</Text>
              <HStack>
                <Text fontSize="sm" color="gray.600">
                  Tip: {chartInfo.chart_type || 'Bilinmiyor'}
                </Text>
                <IconButton
                  aria-label="Yeni grafik oluştur"
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
                  Veri Noktaları: {chartInfo.data_points} | Sütunlar: {chartInfo.columns?.join(', ')}
                </Text>
                
                {chartInfo.fallback && (
                  <Alert status="info">
                    <AlertIcon />
                    <Text fontSize="sm">Plotly.js render kullanılıyor (PNG dışa aktarma başarısız)</Text>
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
                  <Text color="gray.500">Grafik yükleniyor...</Text>
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
            <Text color="red.500" mb={4}>Grafik render edilirken hata</Text>
            <Button 
              colorScheme="gray" 
              onClick={generateChart}
              leftIcon={<ViewIcon />}
            >
              Grafiği Yeniden Oluştur
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

  const deleteQuery = async (sessionId: string, queryId: string) => {
    try {
      // Backend'e silme isteği gönder
      const response = await axios.delete(`${API_URL}/sessions/${sessionId}/queries/${queryId}`);
      
      if (response.data.success) {
        // Frontend'den de kaldır
        setHistory(prev => prev.map(session => {
          if (session.id === sessionId) {
            return {
              ...session,
              queries: session.queries.filter(q => q.id !== queryId)
            };
          }
          return session;
        }).filter(session => session.queries.length > 0));
        
        toast({
          title: "Sorgu Silindi",
          description: "Sorgu geçmişten başarıyla kaldırıldı",
          status: "success",
          duration: 2000,
          isClosable: true,
        });
      } else {
        toast({
          title: "Hata",
          description: response.data.message || "Sorgu silinemedi",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (error) {
      console.error('Error deleting query:', error);
      toast({
        title: "Hata",
        description: "Sorgu silinirken bir hata oluştu",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const groupHistoryByDate = (history: HistoryItem[]) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Start of today
    
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    const groups: { [key: string]: HistoryItem[] } = {
      'Bugün': [],
      'Dün': [],
      'Bu Hafta': [],
      'Bu Ay': [],
      'Daha Eski': []
    };
    
    history.forEach(session => {
      session.queries.forEach(query => {
        const queryDate = new Date(query.timestamp);
        queryDate.setHours(0, 0, 0, 0); // Start of query date
        
        const diffTime = today.getTime() - queryDate.getTime();
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) {
          groups['Bugün'].push({ ...session, queries: [query] });
        } else if (diffDays === 1) {
          groups['Dün'].push({ ...session, queries: [query] });
        } else if (diffDays <= 7) {
          groups['Bu Hafta'].push({ ...session, queries: [query] });
        } else if (diffDays <= 30) {
          groups['Bu Ay'].push({ ...session, queries: [query] });
        } else {
          groups['Daha Eski'].push({ ...session, queries: [query] });
        }
      });
    });
    
    return groups;
  };

  

  return (
    <Box minH="100vh" bg="gray.50">
      {/* Modern Header */}
      <Box 
        borderBottom="1px" 
        borderColor="gray.100" 
        px={4} 
        py={1}
        h="80px"
        position="sticky"
        top={0}
        zIndex={10}
        backdropFilter="blur(20px)"
        bg="rgba(255, 255, 255, 0.95)"
        boxShadow="0 1px 3px rgba(0, 0, 0, 0.05)"
      >
        <Container maxW="7xl">
                      <HStack justify="space-between" align="flex-start">
                            <HStack spacing={0} align="flex-start" ml={-10} pt={0} mt={-2}>
                <Image
                  src="/assets/247b5df2eca666f9b7fc7d57907d4bd041dea7afba62f9f0f8b22e8e9e285702.png"
                  alt="BilişimAI Logo"
                  h="72px"
                  w="auto"
                  objectFit="contain"
                  cursor="pointer"
                  onClick={handleNewChat}
                  _hover={{ transform: "scale(1.02)" }}
                  transition="transform 0.2s"
                  mt={0}
                />
              </HStack>
            
            <HStack spacing={3} align="center" mt={4}>
              {/* Mobile menu button */}
              {!isDesktop && (
                <IconButton
                  aria-label="Open sidebar"
                  icon={<HamburgerIcon />}
                  onClick={() => setSidebarOpen(true)}
                  variant="ghost"
                  size="sm"
                  color="gray.600"
                />
              )}
              
              {/* User Profile */}
              <Box
                w={8}
                h={8}
                borderRadius="full"
                bg="gray.100"
                display="flex"
                alignItems="center"
                justifyContent="center"
                color="gray.600"
                fontSize="sm"
                fontWeight="medium"
                cursor="pointer"
                _hover={{ bg: "gray.200" }}
                transition="all 0.2s"
              >
                AE
              </Box>
            </HStack>
          </HStack>
        </Container>
      </Box>

      {/* Main Layout with Sidebar */}
      <Flex h="calc(100vh - 80px)">
        {/* Desktop Sidebar */}
        {isDesktop && (
          <Box
            w={sidebarCollapsed ? "60px" : "320px"}
            bg="white"
            borderRight="1px"
            borderColor="gray.100"
            transition="width 0.3s ease"
            overflow="hidden"
            position="relative"
            boxShadow="0 2px 8px rgba(0, 0, 0, 0.04)"
          >
            {sidebarCollapsed ? (
              // Collapsed sidebar
              <VStack spacing={4} py={4} align="center">
                <IconButton
                  aria-label="Toggle sidebar"
                  icon={<HamburgerIcon />}
                  onClick={() => setSidebarCollapsed(false)}
                  variant="ghost"
                  size="sm"
                  colorScheme="gray"
                  _hover={{ bg: "gray.100" }}
                />
                <IconButton
                  aria-label="Yeni Sohbet"
                  icon={<AddIcon />}
                  onClick={handleNewChat}
                  variant="ghost"
                  size="sm"
                  colorScheme="gray"
                  _hover={{ bg: "gray.100" }}
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
                  borderColor="gray.100"
                >
                  <HStack justify="space-between" align="center">
                    <HStack spacing={2} align="center">
                      <IconButton
                        aria-label="Toggle sidebar"
                        icon={<HamburgerIcon />}
                        size="sm"
                        variant="ghost"
                        colorScheme="gray"
                        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                        _hover={{ bg: "gray.100" }}
                      />
                      <Text fontSize="lg" fontWeight="medium" color="gray.800">
                        Sohbet Geçmişi
                      </Text>
                    </HStack>
                    <HStack spacing={2}>
                      <IconButton
                        aria-label="Yeni Sohbet"
                        icon={<AddIcon />}
                        onClick={handleNewChat}
                        variant="ghost"
                        size="sm"
                        colorScheme="gray"
                        _hover={{ bg: "gray.100" }}
                      />
                    </HStack>
                  </HStack>
                </Box>
                
                {/* History List */}
                <Box flex={1} overflowY="auto" p={4}>
                  {loadingHistory ? (
                    <VStack spacing={4} py={8}>
                      <Spinner size="md" color="red.500" />
                      <Text fontSize="sm" color="gray.600">Geçmiş yükleniyor...</Text>
                    </VStack>
                  ) : history.length > 0 ? (
                    <VStack spacing={4} align="stretch">
                      {Object.entries(groupHistoryByDate(history)).map(([dateGroup, queries]) => {
                        if (queries.length === 0) return null;
                        
                        return (
                          <Box key={dateGroup}>
                            {/* Date Group Header */}
                            <Text 
                              fontSize="xs" 
                              fontWeight="bold" 
                              color="gray.500" 
                              textTransform="uppercase" 
                              letterSpacing="wide"
                              mb={3}
                              px={2}
                            >
                              {dateGroup}
                            </Text>
                            
                            {/* Queries in this date group */}
                            <VStack spacing={1} align="stretch">
                              {queries.map((item, index) => (
                                                                <Box
                                  key={`${item.id}-${index}`}
                                  py={2}
                                  px={2}
                                  bg="transparent"
                                  cursor="pointer"
                                  onClick={() => {
                                    console.log('History item clicked:', item.queries[0]);
                                    loadQueryFromHistory(item.queries[0]);
                                  }}
                                  _hover={{ 
                                    bg: "gray.50",
                                  }}
                                  transition="all 0.2s"
                                  borderBottom="1px"
                                  borderColor="gray.100"
                                  position="relative"
                                >
                                  <HStack spacing={3} align="center" justify="space-between">
                                    <VStack spacing={1} align="start" flex={1}>
                                      <Text fontSize="sm" fontWeight="medium" color="gray.800" noOfLines={2}>
                                        {item.queries[0].natural_query}
                                      </Text>
                                      <HStack spacing={2} justify="space-between" w="full">
                                        <Text fontSize="xs" color="gray.500">
                                          {formatTimestampToTurkeyTime(item.queries[0].timestamp)}
                                        </Text>

                                      </HStack>
                                    </VStack>
                                    
                                    {/* Delete Button */}
                                    <IconButton
                                      aria-label="Sorguyu sil"
                                      icon={<DeleteIcon />}
                                      size="xs"
                                      variant="ghost"
                                      colorScheme="red"
                                      opacity={0.6}
                                      _hover={{ 
                                        opacity: 1,
                                        bg: "red.50",
                                        color: "red.600"
                                      }}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        if (item.id && item.queries[0].id) {
                                          deleteQuery(item.id, item.queries[0].id);
                                        }
                                      }}
                                    />
                                  </HStack>
                                  
                                </Box>
                              ))}
                            </VStack>
                          </Box>
                        );
                      })}
                    </VStack>
                  ) : (
                    <Box textAlign="center" py={8}>
                      <Text color="gray.500" fontSize="sm">
                        Henüz sorgu yok
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        Geçmişi görmek için soru sormaya başlayın
                      </Text>
                    </Box>
                  )}
                </Box>
              </VStack>
            )}
          </Box>
        )}

        {/* Main Content Area */}
        <Box flex={1} overflowY="auto" pb="100px">
          <Container maxW="6xl" py={6}>
        <VStack spacing={6} align="stretch">


          {/* AImet Welcome Message - Only show when no results */}
          {!result && !loading && (
            <Box
              bg="white"
              borderRadius="xl"
              p={8}
              textAlign="center"
              boxShadow="0 2px 12px rgba(0, 0, 0, 0.04)"
              border="1px"
              borderColor="gray.100"
              maxW="2xl"
              mx="auto"
            >
              <VStack spacing={6}>
                <HStack spacing={4} align="center">
                  <Image
                    src="/assets/247b5df2eca666f9b7fc7d57907d4bd041dea7afba62f9f0f8b22e8e9e285702.png"
                    alt="AImet Mascot"
                    w={24}
                    h={24}
                  />
                  <Heading size="lg" color="gray.800" fontWeight="medium">
                    Merhaba, Ben AImet!
                  </Heading>
                </HStack>
                
                <Text fontSize="md" color="gray.600" textAlign="center">
                  Bugün size nasıl yardımcı olabilirim? İK verileriniz hakkında herhangi bir şey sorun, analiz edeyim.
                </Text>
                
                {/* Example Queries */}
                <VStack spacing={4} w="full" maxW="2xl">
                  <Text fontSize="sm" color="gray.500" fontWeight="medium" textTransform="uppercase" letterSpacing="wide">
                    Bu örnekleri deneyin:
                  </Text>
                  <VStack spacing={3} w="full">
                    {[
                      "Departmana göre çalışan sayısını göster",
                      "Pozisyona göre ortalama maaş nedir?",
                      "En yüksek bağlılık puanına sahip çalışanlar kimler?",
                      "Geçen ay kaç kişi işe alındı?",
                      "Takıma göre eğitim tamamlama oranı nedir?"
                    ].map((example, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        size="md"
                        w="full"
                        justifyContent="flex-start"
                        textAlign="left"
                        colorScheme="gray"
                        borderColor="gray.200"
                        color="gray.700"
                        _hover={{
                          bg: "gray.50",
                          borderColor: "gray.300",
                          transform: "translateY(-1px)"
                        }}
                        onClick={() => setQuery(example)}
                        transition="all 0.2s"
                      >
                        {example}
                      </Button>
                    ))}
                  </VStack>
                </VStack>
              </VStack>
            </Box>
          )}

          {/* Loading State */}
          {loading && (
            <Box
              bg="white"
              borderRadius="xl"
              p={12}
              textAlign="center"
              boxShadow="0 2px 12px rgba(0, 0, 0, 0.04)"
              border="1px"
              borderColor="gray.100"
            >
              <VStack spacing={6}>
                <Spinner size="xl" color="gray.500" thickness="3px" />
                <VStack spacing={2}>
                  <Text fontSize="xl" fontWeight="medium" color="gray.800">
                    Sorgunuz AI ile analiz ediliyor
                  </Text>
                  <Text fontSize="sm" color="gray.600">
                    Bu işlem birkaç dakika sürebilir...
                  </Text>
                </VStack>
              </VStack>
            </Box>
          )}

          {/* Live Streaming Chat Steps */}
          {isStreaming && chatSteps.length > 0 && (
            <Box
              bg="transparent"
              mb={6}
              px={4}
            >
              <VStack spacing={4} align="stretch">
                {chatSteps.map((step, index) => (
                  <Box
                    key={index}
                    alignSelf="flex-start"
                    maxW="75%"
                    bg="white"
                    p={4}
                    borderRadius="2xl"
                    border="1px"
                    borderColor="gray.100"
                    boxShadow="0 1px 3px rgba(0, 0, 0, 0.05)"
                    transition="all 0.2s ease"
                    _hover={{ transform: 'translateY(-1px)', boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)' }}
                  >
                    <HStack spacing={3} mb={3} align="center">
                      <Image
                        src="/assets/247b5df2eca666f9b7fc7d57907d4bd041dea7afba62f9f0f8b22e8e9e285702.png"
                        alt="AImet Mascot"
                        w={6}
                        h={6}
                        borderRadius="full"
                        objectFit="cover"
                        flexShrink={0}
                      />
                      <Text fontSize="sm" fontWeight="medium" color="gray.700" textTransform="uppercase" letterSpacing="wide">
                        {step.type === 'explanation' && 'Analiz'}
                        {step.type === 'sql' && 'SQL Sorgusu'}
                        {step.type === 'results' && 'Veri'}
                        {step.type === 'chart' && 'Grafik'}
                      </Text>
                      {step.status === 'loading' && (
                        <Spinner size="sm" color="gray.500" />
                      )}
                      {step.status === 'complete' && (
                        <Icon as={CheckIcon} color="green.500" boxSize={4} />
                      )}
                    </HStack>
                    
                    {step.type === 'explanation' && (
                      <Text color="gray.700" fontSize="md" lineHeight="1.6">
                        {step.content}
                      </Text>
                    )}
                    
                    {step.type === 'sql' && (
                      <Box
                        bg="gray.50"
                        p={3}
                        borderRadius="lg"
                        border="1px"
                        borderColor="gray.100"
                        overflow="auto"
                        maxW="100%"
                      >
                        <Code color="gray.800" fontSize="xs" whiteSpace="pre-wrap" bg="transparent">
                          {step.content}
                        </Code>
                      </Box>
                    )}
                    
                    {step.type === 'results' && (
                      <Box>
                        <Text fontSize="sm" color="gray.600" mb={3}>
                          {step.content.length} satır döndürüldü
                        </Text>
                        <Box
                          bg="gray.50"
                          p={3}
                          borderRadius="lg"
                          border="1px"
                          borderColor="gray.100"
                          maxH="200px"
                          overflow="auto"
                        >
                          <Table variant="simple" size="sm">
                            <Thead>
                              <Tr>
                                {Object.keys(step.content[0] || {}).map(key => (
                                  <Th key={key} fontSize="xs" py={2} px={3} color="gray.700" fontWeight="medium">{key}</Th>
                                ))}
                              </Tr>
                            </Thead>
                            <Tbody>
                              {step.content.map((row: any, idx: number) => (
                                <Tr key={idx} _hover={{ bg: "gray.100" }}>
                                  {Object.values(row).map((value: any, valIdx: number) => (
                                    <Td key={valIdx} fontSize="xs" py={2} px={3} color="gray.800">{String(value)}</Td>
                                  ))}
                                </Tr>
                              ))}
                            </Tbody>
                          </Table>
                        </Box>
                      </Box>
                    )}
                    
                    {step.type === 'chart' && (
                      <Box>
                        {step.content.chart_data && step.content.chart_data.startsWith('data:image/') ? (
                          <Image 
                            src={step.content.chart_data} 
                            alt="Data Chart"
                            width="100%"
                            height="300px"
                            borderRadius="md"
                            objectFit="contain"
                            onError={(e) => {
                              console.error('Chat step image load error:', e);
                              console.error('Chart data length:', step.content.chart_data?.length);
                            }}
                            onLoad={() => {
                              console.log('✅ Chat step image loaded successfully');
                            }}
                          />
                        ) : step.content.chart_data ? (
                          <Text color="gray.600" fontSize="sm">Grafik verisi mevcut</Text>
                        ) : (
                          <Text color="gray.600" fontSize="sm">Grafik henüz oluşturulmadı</Text>
                        )}
                      </Box>
                    )}
                  </Box>
                ))}
              </VStack>
            </Box>
          )}

          {/* Results */}
          {result && (
            <Box
              bg="white"
              borderRadius="xl"
              overflow="hidden"
              boxShadow="0 2px 12px rgba(0, 0, 0, 0.04)"
              border="1px"
              borderColor="gray.100"
            >


                  {/* Chat-like Results Display */}
                  <Box p={4}>
                    <VStack spacing={4} align="stretch">
                      {/* User Message - Always show the user's question */}
                      <Box
                        alignSelf="flex-end"
                        maxW="75%"
                        bg="red.600"
                        p={3}
                        borderRadius="2xl"
                        color="white"
                        boxShadow="0 2px 8px rgba(220, 38, 38, 0.2)"
                      >
                        <VStack spacing={1} align="end">
                          <Text fontSize="sm" fontWeight="medium">
                            {result.user_query || result.natural_query}
                          </Text>
                          <Text fontSize="xs" color="red.100">
                            {new Date(result.timestamp).toLocaleString('tr-TR')}
                          </Text>
                        </VStack>
                      </Box>
                      
                      {/* AI Explanation */}
                      <Box
                        alignSelf="flex-start"
                        maxW="75%"
                        bg="white"
                        p={4}
                        borderRadius="2xl"
                        border="1px"
                        borderColor="gray.200"
                        boxShadow="0 2px 8px rgba(0, 0, 0, 0.08)"
                      >
                        <HStack spacing={3} mb={3} align="center">
                          <Image
                            src="/assets/247b5df2eca666f9b7fc7d57907d4bd041dea7afba62f9f0f8b22e8e9e285702.png"
                            alt="AImet Mascot"
                            w={6}
                            h={6}
                            borderRadius="full"
                            objectFit="cover"
                            flexShrink={0}
                          />
                          <Text fontSize="sm" fontWeight="medium" color="gray.700" textTransform="uppercase" letterSpacing="wide">
                            Analiz
                          </Text>
                        </HStack>
                        <Text color="gray.700" fontSize="md" lineHeight="1.5">
                          {result.explanation || 'No explanation available'}
                        </Text>
                      </Box>

                      {/* SQL Query */}
                      <Box
                        alignSelf="flex-start"
                        maxW="75%"
                        bg="white"
                        p={4}
                        borderRadius="2xl"
                        border="1px"
                        borderColor="gray.200"
                        boxShadow="0 2px 8px rgba(0, 0, 0, 0.08)"
                      >
                        <HStack spacing={3} mb={3} align="center" justify="space-between">
                          <HStack spacing={3}>
                            <Image
                              src="/assets/247b5df2eca666f9b7fc7d57907d4bd041dea7afba62f9f0f8b22e8e9e285702.png"
                              alt="AImet Mascot"
                              w={6}
                              h={6}
                              borderRadius="full"
                              objectFit="cover"
                              flexShrink={0}
                            />
                            <Text fontSize="sm" fontWeight="medium" color="gray.700" textTransform="uppercase" letterSpacing="wide">
                              SQL Sorgusu
                            </Text>
                          </HStack>
                            <Button
                              size="sm"
                              variant="ghost"
                              colorScheme="gray"
                              onClick={() => {
                                navigator.clipboard.writeText(result.sql_query);
                                toast({
                                  title: "SQL Kopyalandı!",
                                  description: "SQL sorgusu panoya kopyalandı",
                                  status: "success",
                                  duration: 2000,
                                  isClosable: true,
                                });
                              }}
                              leftIcon={<Icon as={CopyIcon} />}
                            >
                              Kopyala
                            </Button>
                        </HStack>
                        <Box
                          bg="gray.50"
                          p={3}
                          borderRadius="lg"
                          border="1px"
                          borderColor="gray.200"
                          overflow="auto"
                          maxW="100%"
                        >
                          <Code color="gray.800" fontSize="xs" whiteSpace="pre-wrap" bg="transparent">
                            {result.sql_query || 'No SQL query available'}
                          </Code>
                        </Box>
                      </Box>

                      {/* Data Results */}
                      <Box
                        alignSelf="flex-start"
                        maxW="75%"
                        bg="white"
                        p={4}
                        borderRadius="2xl"
                        border="1px"
                        borderColor="gray.200"
                        boxShadow="0 2px 8px rgba(0, 0, 0, 0.08)"
                      >
                        <HStack spacing={3} mb={3} align="center">
                          <Image
                            src="/assets/247b5df2eca666f9b7fc7d57907d4bd041dea7afba62f9f0f8b22e8e9e285702.png"
                            alt="AImet Mascot"
                            w={6}
                            h={6}
                            borderRadius="full"
                            objectFit="cover"
                            flexShrink={0}
                          />
                          <Text fontSize="sm" fontWeight="medium" color="gray.700" textTransform="uppercase" letterSpacing="wide">
                            Veri Sonuçları ({result.results ? result.results.length : 0} satır)
                          </Text>
                        </HStack>
                        
                        {result.results && result.results.length > 0 ? (
                          <Box
                            bg="gray.50"
                            p={3}
                            borderRadius="lg"
                            border="1px"
                            borderColor="gray.200"
                            maxH="250px"
                            overflow="auto"
                          >
                            <Table variant="simple" size="sm">
                              <Thead>
                                <Tr>
                                  {Object.keys(result.results[0] || {}).map((key) => (
                                    <Th key={key} fontSize="xs" py={2} px={3} color="gray.700" fontWeight="semibold">{key}</Th>
                                  ))}
                                </Tr>
                              </Thead>
                              <Tbody>
                                {result.results.map((row, index) => (
                                  <Tr key={index} _hover={{ bg: "gray.100" }}>
                                    {Object.values(row || {}).map((value, cellIndex) => (
                                      <Td key={cellIndex} py={2} px={3} fontSize="xs" color="gray.800">
                                        {String(value || '')}
                                      </Td>
                                    ))}
                                  </Tr>
                                ))}
                              </Tbody>
                            </Table>
                          </Box>
                        ) : (
                          <Text color="gray.500" fontSize="sm">
                            Bu sorgu için sonuç bulunamadı
                          </Text>
                        )}
                      </Box>

                      {/* Data Visualization */}
                      {result.chart_data && (
                        <Box
                          alignSelf="flex-start"
                          maxW="75%"
                          bg="white"
                          p={4}
                          borderRadius="2xl"
                          border="1px"
                          borderColor="gray.200"
                          boxShadow="0 2px 8px rgba(0, 0, 0, 0.08)"
                        >
                          <HStack spacing={3} mb={3} align="center">
                            <Image
                              src="/assets/247b5df2eca666f9b7fc7d57907d4bd041dea7afba62f9f0f8b22e8e9e285702.png"
                              alt="AImet Mascot"
                              w={6}
                              h={6}
                              borderRadius="full"
                              objectFit="cover"
                              flexShrink={0}
                            />
                            <Text fontSize="sm" fontWeight="medium" color="gray.700" textTransform="uppercase" letterSpacing="wide">
                              Grafik
                            </Text>
                          </HStack>
                          {renderChart()}
                        </Box>
                      )}
                    </VStack>
                  </Box>
            </Box>
          )}
            </VStack>
          </Container>
              </Box>
        
        {/* Fixed Chat Input at Bottom */}
        <Box
          position="fixed"
          bottom={0}
          left={isDesktop && !sidebarCollapsed ? "320px" : "0px"}
          right={0}
          bg="transparent"
          p={4}
          zIndex={20}
          transition="left 0.3s ease"
        >
          <Container maxW="4xl">
            <HStack 
              spacing={3} 
              as="form" 
              onSubmit={handleSubmit}
              bg="white"
              p={4}
              borderRadius="2xl"
              border="1px"
              borderColor="gray.200"
              boxShadow="0 4px 20px rgba(0, 0, 0, 0.08)"
            >
              <Input
                placeholder="İK verileriniz hakkında herhangi bir şey sorun..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                size="lg"
                borderRadius="xl"
                border="1px"
                borderColor="gray.200"
                _focus={{
                  borderColor: "gray.400",
                  boxShadow: "0 0 0 3px rgba(0, 0, 0, 0.05)"
                }}
                _hover={{ borderColor: "gray.300" }}
                onKeyPress={(e) => e.key === 'Enter' && handleSubmit(e)}
                bg="white"
                flex={1}
                fontSize="md"
              />
              <Button
                type="submit"
                colorScheme="red"
                size="lg"
                px={6}
                py={5}
                fontSize="md"
                fontWeight="medium"
                borderRadius="xl"
                boxShadow="0 2px 8px rgba(0, 0, 0, 0.1)"
                isLoading={loading}
                loadingText="Çalıştırılıyor..."
                _hover={{
                  transform: "translateY(-1px)",
                  boxShadow: "0 4px 15px rgba(0, 0, 0, 0.15)"
                }}
                transition="all 0.2s"
              >
                <Icon as={ArrowUpIcon} />
              </Button>
            </HStack>
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
          <DrawerHeader bg="gray.50" borderBottom="1px" borderColor="gray.100">
            <Text color="gray.800" fontWeight="medium">Sohbet Geçmişi</Text>
          </DrawerHeader>
          <DrawerBody p={4}>
            {loadingHistory ? (
              <VStack spacing={4} py={8}>
                <Spinner size="md" color="gray.500" />
                <Text fontSize="sm" color="gray.600">Geçmiş yükleniyor...</Text>
              </VStack>
            ) : history.length > 0 ? (
              <VStack spacing={0} align="stretch">
                {Object.entries(groupHistoryByDate(history)).map(([dateGroup, queries]) => {
                  if (queries.length === 0) return null;
                  
                  return (
                    <Box key={dateGroup}>
                      {/* Date Group Header */}
                      <Text 
                        fontSize="xs" 
                        fontWeight="medium" 
                        color="gray.500" 
                        textTransform="uppercase" 
                        letterSpacing="wide"
                        mb={3}
                        px={2}
                      >
                        {dateGroup}
                      </Text>
                      
                      {/* Queries in this date group */}
                      <VStack spacing={1} align="stretch">
                        {queries.map((item, index) => (
                          <Box
                            key={`${item.id}-${index}`}
                            py={2}
                            px={2}
                            bg="transparent"
                            cursor="pointer"
                            onClick={() => {
                              console.log('History item clicked:', item.queries[0]);
                              loadQueryFromHistory(item.queries[0]);
                              setSidebarOpen(false); // Close drawer after selection
                            }}
                            _hover={{ 
                              bg: "gray.50",
                            }}
                            transition="all 0.2s"
                            borderBottom="1px"
                            borderColor="gray.100"
                            position="relative"
                          >
                            <HStack spacing={3} align="center" justify="space-between">
                              <VStack spacing={1} align="start" flex={1}>
                                <Text fontSize="sm" fontWeight="medium" color="gray.800" noOfLines={2}>
                                  {item.queries[0].natural_query}
                                </Text>
                                <HStack spacing={2} justify="space-between" w="full">
                                  <Text fontSize="xs" color="gray.500">
                                    {formatTimestampToTurkeyTime(item.queries[0].timestamp)}
                                  </Text>

                                </HStack>
                              </VStack>
                              
                              {/* Delete Button */}
                              <IconButton
                                aria-label="Sorguyu sil"
                                icon={<DeleteIcon />}
                                size="xs"
                                variant="ghost"
                                colorScheme="red"
                                opacity={0.6}
                                _hover={{ 
                                  opacity: 1,
                                  bg: "red.50",
                                  color: "red.600"
                                }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (item.id && item.queries[0].id) {
                                    deleteQuery(item.id, item.queries[0].id);
                                  }
                                }}
                              />
                            </HStack>
                          </Box>
                        ))}
                      </VStack>
                    </Box>
                  );
                })}
              </VStack>
            ) : (
              <Box textAlign="center" py={8}>
                <Text color="gray.500" fontSize="sm">
                  Henüz sorgu yok
                </Text>
                <Text color="gray.400" fontSize="xs">
                  Geçmişi görmek için soru sormaya başlayın
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
          <ModalHeader bg="gray.50" color="gray.800" borderBottom="1px" borderColor="gray.100">Veri Görselleştirme</ModalHeader>
          <ModalCloseButton color="gray.600" />
          <ModalBody pb={6} pt={4}>
            {result?.chart_data && (
              <Image 
                src={result.chart_data} 
                alt="Data Chart" 
                w="full" 
                h="auto"
                borderRadius="md"
              />
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </Box>
  )
}

export default App 