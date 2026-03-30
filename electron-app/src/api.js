import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
});

export const checkHealth = async () => {
  try {
    const res = await api.get('/health');
    return res.data;
  } catch (e) {
    throw e;
  }
};

export const sendQuery = async (query, parameters = {}) => {
  try {
    const res = await api.post('/query', {
      query,
      parameters: {
        max_new_tokens: 512,
        temperature: 0.7,
        top_p: 0.95,
        ...parameters
      }
    });
    return res.data;
  } catch (e) {
    throw e;
  }
};
