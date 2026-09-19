import { setupServer } from 'msw/node';

import { handlers } from './handlers';

/** MSW server shared by every test. Tests override handlers with `server.use(...)`. */
export const server = setupServer(...handlers);
