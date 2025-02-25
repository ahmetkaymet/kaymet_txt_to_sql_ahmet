# Natural Language to SQL Converter Frontend

The frontend application for the Natural Language to SQL Converter, built with Next.js and Chakra UI.

## Features

- **Modern UI**: Clean and responsive interface built with Chakra UI
- **Real-time Processing**: Instant query processing and result display
- **Session Management**: Organize queries into logical sessions
- **Query History**: Browse and review past queries and their results
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Dark Mode**: Built-in dark mode support for better user experience

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **UI Library**: Chakra UI
- **State Management**: React Hooks
- **HTTP Client**: Axios
- **TypeScript**: For type safety and better developer experience
- **ESLint**: For code quality and consistency

## Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── components/        # Reusable React components
│   ├── providers/        # Context providers
│   ├── styles/          # Global styles and theme
│   ├── layout.tsx       # Root layout component
│   └── page.tsx         # Main page component
├── public/               # Static assets
└── package.json         # Project dependencies and scripts
```

## Components

### Main Page (`app/page.tsx`)
- Main interface for the application
- Handles query input and submission
- Displays query history and results
- Manages sessions and error states

### ClientOnly (`components/ClientOnly.tsx`)
- Prevents hydration mismatch
- Ensures components only render on client side
- Improves initial page load experience

## Setup and Development

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env.local
```

3. Start development server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
```

5. Start production server:
```bash
npm start
```

## Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000  # Backend API URL
```

## API Integration

The frontend communicates with the backend through several endpoints:

### Execute Query
```typescript
POST /execute-sql
{
  query: string;
  session_id?: string;
}
```

### Get Sessions
```typescript
GET /sessions
```

### Error Handling

The application handles various error scenarios:
- Network connectivity issues
- Server errors
- Invalid responses
- Rate limiting
- Timeout errors

## State Management

The application manages several pieces of state:
- Current query input
- Loading states
- Query results
- Session data
- Error states

## Contributing

1. Fork the repository
2. Create your feature branch
3. Install dependencies
4. Make your changes
5. Run tests
6. Submit a pull request

## Scripts

- `npm run dev`: Start development server
- `npm run build`: Build for production
- `npm start`: Start production server
- `npm run lint`: Run ESLint
- `npm run type-check`: Run TypeScript compiler
- `npm test`: Run tests

## Browser Support

The application supports all modern browsers:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Performance Optimization

- Code splitting
- Image optimization
- Font optimization
- CSS-in-JS optimization
- Server-side rendering
- Static generation where possible

## Accessibility

The application follows WCAG guidelines:
- Proper heading hierarchy
- ARIA labels
- Keyboard navigation
- Color contrast
- Screen reader support

## License

This project is licensed under the MIT License.
