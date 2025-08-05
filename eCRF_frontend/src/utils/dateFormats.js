import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';

dayjs.extend(customParseFormat);

const dateFormats = [
  {
    id: 'DD-MM-YYYY',
    label: 'Day-Month-Year',
    description: 'e.g., 01-08-2025',
    example: dayjs().format('DD-MM-YYYY'),
    inputType: 'text'
  },
  {
    id: 'MM-DD-YYYY',
    label: 'Month-Day-Year',
    description: 'e.g., 08-01-2025',
    example: dayjs().format('MM-DD-YYYY'),
    inputType: 'text'
  },
  {
    id: 'YYYY-MM-DD',
    label: 'Year-Month-Day',
    description: 'e.g., 2025-08-01',
    example: dayjs().format('YYYY-MM-DD'),
    inputType: 'text'
  },
  {
    id: 'DD/MM/YYYY',
    label: 'Day/Month/Year',
    description: 'e.g., 01/08/2025',
    example: dayjs().format('DD/MM/YYYY'),
    inputType: 'text'
  },
  {
    id: 'MM/DD/YYYY',
    label: 'Month/Day/Year',
    description: 'e.g., 08/01/2025',
    example: dayjs().format('MM/DD/YYYY'),
    inputType: 'text'
  },
  {
    id: 'YYYY/MM/DD',
    label: 'Year/Month/Day',
    description: 'e.g., 2025/08/01',
    example: dayjs().format('YYYY/MM/DD'),
    inputType: 'text'
  },
  {
    id: 'DD MMM YYYY',
    label: 'Day Month (Short) Year',
    description: 'e.g., 01 Aug 2025',
    example: dayjs().format('DD MMM YYYY'),
    inputType: 'text'
  },
  {
    id: 'YYYY',
    label: 'Year Only',
    description: 'e.g., 2025',
    example: dayjs().format('YYYY'),
    inputType: 'text',
    constraints: { min: 1900, max: 2100 }
  },
  {
    id: 'MM-YYYY',
    label: 'Month-Year',
    description: 'e.g., 08-2025',
    example: dayjs().format('MM-YYYY'),
    inputType: 'text'
  },
  {
    id: 'YYYY-MM-DD HH:mm',
    label: 'Date and Time',
    description: 'e.g., 2025-08-01 14:30',
    example: dayjs().format('YYYY-MM-DD HH:mm'),
    inputType: 'text'
  },
  {
    id: 'YYYY HH:mm',
    label: 'Year and Time',
    description: 'e.g., 2025 14:30',
    example: dayjs().format('YYYY HH:mm'),
    inputType: 'text'
  },
  {
    id: 'HH:mm',
    label: 'Time Only',
    description: 'e.g., 14:30',
    example: dayjs().format('HH:mm'),
    inputType: 'text'
  },
  {
    id: 'YYYY-MM-DD HH:mm:ss',
    label: 'Date and Time with Seconds',
    description: 'e.g., 2025-08-01 14:30:45',
    example: dayjs().format('YYYY-MM-DD HH:mm:ss'),
    inputType: 'text'
  }
];

export default dateFormats;