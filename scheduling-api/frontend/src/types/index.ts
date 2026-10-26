export interface User {
  id: number;
  email: string;
  role: "admin" | "client";
  is_active: boolean;
}
export interface Room {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
}
export interface Interval {
  starts_at: string;
  ends_at: string;
}
export interface Appointment extends Interval {
  id: number;
  user_id: number;
  resource_id: number;
  status: "scheduled" | "cancelled";
}
export interface AppointmentPage {
  items: Appointment[];
  total: number;
  page: number;
  limit: number;
}
export interface Availability {
  free_intervals: Interval[];
  reservation_guaranteed: boolean;
}
