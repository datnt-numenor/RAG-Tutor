"""
Service stubs — business logic layer.

Hierarchy:
  endpoint → service → repository → Prisma DB
                     ↓
               Supabase (Storage, RPC match_chunks, Auth)
"""
from __future__ import annotations
