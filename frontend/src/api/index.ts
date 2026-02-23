import axios from 'axios'
import type { ApiResponse } from '@/types/alert'

const http = axios.create({
  baseURL: '',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.response.use(
  (response) => {
    const data = response.data as ApiResponse<unknown>
    if (data.code !== 200) {
      return Promise.reject(new Error(data.message || 'Request failed'))
    }
    return response
  },
  (error) => {
    return Promise.reject(error)
  },
)

export default http
