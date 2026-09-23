import './globals.css';
import { AuthProvider } from '@/lib/auth';

export const metadata = {
  title: 'ScanIZI — Интеллектуальный анализ товаров и запасов',
  description: 'ScanIZI помогает владельцам бизнеса принимать обоснованные решения по управлению запасами, анализу продаж и оптимизации товарных остатков.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
