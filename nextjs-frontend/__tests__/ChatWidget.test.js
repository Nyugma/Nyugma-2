import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatWidget from '../components/ChatWidget';

// Mock next/navigation
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock getBackendUrl
jest.mock('../utils/api', () => ({
  getBackendUrl: () => 'http://localhost:8000',
}));

// Helper to build a mock fetch response
function mockFetchResponse(data) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(data),
  });
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe('ChatWidget navigation links', () => {
  /**
   * Validates: Requirements 4.3, 4.4
   * Test that navigation link cards render when navigation_links is present in the response.
   */
  test('renders navigation link cards when navigation_links is present in response', async () => {
    const user = userEvent.setup();

    global.fetch = jest.fn(() =>
      mockFetchResponse({
        session_id: 'test-session',
        response: 'Here are some pages you can visit.',
        sources: [],
        navigation_links: [
          { page_name: 'Dashboard', route: '/dashboard', description: 'View your dashboard' },
          { page_name: 'Search', route: '/search', description: 'Search for cases' },
        ],
      })
    );

    render(<ChatWidget />);

    // Open the chat panel
    await user.click(screen.getByLabelText('Open chat assistant'));

    // Type a message and send
    const input = screen.getByLabelText('Chat message input');
    await user.type(input, 'Where is the dashboard?');
    await user.click(screen.getByLabelText('Send message'));

    // Wait for navigation link cards to appear
    await waitFor(() => {
      expect(screen.getByLabelText('Navigate to Dashboard')).toBeInTheDocument();
      expect(screen.getByLabelText('Navigate to Search')).toBeInTheDocument();
    });
  });

  /**
   * Validates: Requirements 4.3
   * Test that clicking a navigation link card triggers router.push with the correct route.
   */
  test('clicking a navigation card triggers navigation to correct route', async () => {
    const user = userEvent.setup();

    global.fetch = jest.fn(() =>
      mockFetchResponse({
        session_id: 'test-session',
        response: 'You can go to the dashboard.',
        sources: [],
        navigation_links: [
          { page_name: 'Dashboard', route: '/dashboard', description: 'View your dashboard' },
        ],
      })
    );

    render(<ChatWidget />);

    await user.click(screen.getByLabelText('Open chat assistant'));

    const input = screen.getByLabelText('Chat message input');
    await user.type(input, 'Take me to the dashboard');
    await user.click(screen.getByLabelText('Send message'));

    await waitFor(() => {
      expect(screen.getByLabelText('Navigate to Dashboard')).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText('Navigate to Dashboard'));

    expect(mockPush).toHaveBeenCalledWith('/dashboard');
  });

  /**
   * Validates: Requirements 4.4
   * Test that navigation cards display page name and description.
   */
  test('navigation cards display page name and description', async () => {
    const user = userEvent.setup();

    global.fetch = jest.fn(() =>
      mockFetchResponse({
        session_id: 'test-session',
        response: 'Here is the inquiry page.',
        sources: [],
        navigation_links: [
          { page_name: 'Inquiry', route: '/inquiry', description: 'Submit a legal inquiry' },
        ],
      })
    );

    render(<ChatWidget />);

    await user.click(screen.getByLabelText('Open chat assistant'));

    const input = screen.getByLabelText('Chat message input');
    await user.type(input, 'How do I submit an inquiry?');
    await user.click(screen.getByLabelText('Send message'));

    await waitFor(() => {
      expect(screen.getByLabelText('Navigate to Inquiry')).toBeInTheDocument();
    });

    const card = screen.getByLabelText('Navigate to Inquiry');
    expect(card).toHaveTextContent('Inquiry');
    expect(card).toHaveTextContent('Submit a legal inquiry');
  });
});
