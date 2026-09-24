import { createClient } from "@supabase/supabase-js";

const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL ??
  "https://xlreazpjvcudvbslrzdw.supabase.co";

const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ??
  "sb_publishable_DcAwNxH9UFhepZ5_wHVOcg_vq25B5WI";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
