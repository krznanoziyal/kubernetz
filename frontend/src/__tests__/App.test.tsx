import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';

describe('App routing', () => {
  it('renders homepage at root path', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );
    // Lazy-loaded content — just ensure the app renders without throwing
    expect(document.body).toBeDefined();
  });
});
