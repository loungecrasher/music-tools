"""
Streamlit Web UI for Music Tools
Modern web-based interface as an alternative to terminal UI

Features:
- Dashboard with library statistics and visualizations
- Smart Cleanup workflow (8-step duplicate detection/removal)
- Library Stats with detailed analytics
- Settings for Spotify/Deezer configuration

Author: Music Tools Dev Team
Created: 2026-01-08
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import logging
from typing import Optional, Dict, List, Any
import json
import os

# Import Music Tools modules
from src.library.database import LibraryDatabase
from src.library.duplicate_checker import DuplicateChecker
from src.library.quality_analyzer import extract_audio_metadata, rank_duplicate_group, get_quality_tier
from src.library.safe_delete import SafeDeletionPlan, DeletionStats
from src.library.models import LibraryFile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Music Tools",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Color scheme
COLORS = {
    'spotify_green': '#1DB954',
    'deezer_pink': '#FF5500',
    'background': '#121212',
    'card_bg': '#282828',
    'text_primary': '#FFFFFF',
    'text_secondary': '#B3B3B3',
    'success': '#1DB954',
    'warning': '#FFA500',
    'error': '#FF0000',
    'info': '#00D4FF'
}

# Custom CSS
st.markdown(f"""
<style>
    .main {{
        background-color: {COLORS['background']};
    }}
    .stMetric {{
        background-color: {COLORS['card_bg']};
        padding: 15px;
        border-radius: 10px;
    }}
    .metric-card {{
        background: linear-gradient(135deg, {COLORS['card_bg']} 0%, #383838 100%);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 10px;
    }}
    .success-badge {{
        background-color: {COLORS['success']};
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
    }}
    .warning-badge {{
        background-color: {COLORS['warning']};
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
    }}
    .error-badge {{
        background-color: {COLORS['error']};
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
    }}
    h1, h2, h3 {{
        color: {COLORS['text_primary']};
    }}
    p, label {{
        color: {COLORS['text_secondary']};
    }}
</style>
""", unsafe_allow_html=True)


# Initialize session state
def init_session_state():
    """Initialize Streamlit session state variables"""
    if 'db_path' not in st.session_state:
        st.session_state.db_path = str(Path.home() / '.music_tools' / 'library.db')
    if 'library_path' not in st.session_state:
        st.session_state.library_path = str(Path.home() / 'Music')
    if 'scan_results' not in st.session_state:
        st.session_state.scan_results = None
    if 'duplicate_groups' not in st.session_state:
        st.session_state.duplicate_groups = []
    if 'cleanup_step' not in st.session_state:
        st.session_state.cleanup_step = 1
    if 'scan_mode' not in st.session_state:
        st.session_state.scan_mode = 'deep'
    if 'confirmed_groups' not in st.session_state:
        st.session_state.confirmed_groups = set()


def get_library_db() -> Optional[LibraryDatabase]:
    """Get or create LibraryDatabase instance"""
    try:
        db_path = Path(st.session_state.db_path)
        if not db_path.exists():
            st.warning(f"Database not found at {db_path}. Please configure database path in Settings.")
            return None
        return LibraryDatabase(str(db_path))
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        logger.error(f"Database connection error: {e}", exc_info=True)
        return None


# ============================================================================
# DASHBOARD PAGE
# ============================================================================

def render_dashboard():
    """Render main dashboard with library statistics and charts"""
    st.title("🎵 Music Tools Dashboard")

    db = get_library_db()
    if not db:
        st.info("Configure your library path in Settings to get started.")
        return

    # Get library statistics
    try:
        stats = db.get_statistics()
    except Exception as e:
        st.error(f"Error loading statistics: {e}")
        return

    # Metrics cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Playlists",
            value=stats.playlists_count or "N/A",
            delta=None
        )

    with col2:
        st.metric(
            label="Total Tracks",
            value=f"{stats.total_files:,}" if stats.total_files else "0",
            delta=None
        )

    with col3:
        st.metric(
            label="Library Size",
            value=f"{stats.total_size_gb:.2f} GB" if stats.total_size_gb else "0 GB",
            delta=None
        )

    with col4:
        last_scan = stats.last_scan_date or "Never"
        if isinstance(last_scan, datetime):
            last_scan = last_scan.strftime("%Y-%m-%d")
        st.metric(
            label="Last Scan",
            value=last_scan,
            delta=None
        )

    st.markdown("---")

    # Charts row 1: Playlist distribution and Library growth
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Playlist Distribution")

        # Mock data - replace with actual Spotify/Deezer playlist counts
        playlist_data = {
            'Source': ['Spotify', 'Deezer', 'Local'],
            'Count': [45, 23, 12]
        }

        fig = px.pie(
            playlist_data,
            values='Count',
            names='Source',
            color='Source',
            color_discrete_map={
                'Spotify': COLORS['spotify_green'],
                'Deezer': COLORS['deezer_pink'],
                'Local': '#888888'
            },
            hole=0.4
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color=COLORS['text_primary'],
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📈 Library Growth Over Time")

        # Mock data - replace with actual growth tracking
        dates = pd.date_range(end=datetime.now(), periods=12, freq='ME')
        growth_data = pd.DataFrame({
            'Date': dates,
            'Tracks': [1200, 1350, 1420, 1580, 1650, 1720, 1800, 1920, 2050, 2180, 2300, stats.total_files or 2400]
        })

        fig = px.line(
            growth_data,
            x='Date',
            y='Tracks',
            markers=True
        )
        fig.update_traces(line_color=COLORS['spotify_green'], marker_size=8)
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color=COLORS['text_primary'],
            xaxis_title="Month",
            yaxis_title="Total Tracks"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Recent playlists table
    st.subheader("📝 Recent Playlists")

    # Mock data - replace with actual recent playlists
    recent_playlists = pd.DataFrame({
        'Playlist': ['Workout Mix', 'Chill Vibes', 'Electronic Focus', 'Jazz Classics', 'Rock Essentials'],
        'Source': ['Spotify', 'Deezer', 'Spotify', 'Local', 'Spotify'],
        'Tracks': [45, 32, 67, 28, 52],
        'Last Updated': ['2026-01-08', '2026-01-07', '2026-01-06', '2026-01-05', '2026-01-04']
    })

    st.dataframe(
        recent_playlists,
        use_container_width=True,
        hide_index=True
    )


# ============================================================================
# SMART CLEANUP PAGE
# ============================================================================

def render_smart_cleanup():
    """Render Smart Cleanup 8-step workflow"""
    st.title("🧹 Smart Cleanup")

    step = st.session_state.cleanup_step

    # Progress indicator
    progress_cols = st.columns(8)
    for i in range(8):
        with progress_cols[i]:
            if i + 1 < step:
                st.markdown(f"<div style='text-align: center; color: {COLORS['success']};'>✓ {i+1}</div>", unsafe_allow_html=True)
            elif i + 1 == step:
                st.markdown(f"<div style='text-align: center; color: {COLORS['info']};'>● {i+1}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align: center; color: {COLORS['text_secondary']};'>○ {i+1}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Step 1: Library Path Selection
    if step == 1:
        render_cleanup_step1()

    # Step 2: Scan Mode Selection
    elif step == 2:
        render_cleanup_step2()

    # Step 3: Scanning Progress
    elif step == 3:
        render_cleanup_step3()

    # Step 4: Review Duplicates
    elif step == 4:
        render_cleanup_step4()

    # Step 5: Quality Distribution
    elif step == 5:
        render_cleanup_step5()

    # Step 6: Confirmation
    elif step == 6:
        render_cleanup_step6()

    # Step 7: Execute
    elif step == 7:
        render_cleanup_step7()

    # Step 8: Completion
    elif step == 8:
        render_cleanup_step8()


def render_cleanup_step1():
    """Step 1: Library path selection"""
    st.subheader("Step 1: Select Library Path")

    st.info("Select the music library folder to scan for duplicates.")

    library_path = st.text_input(
        "Library Path",
        value=st.session_state.library_path,
        help="Enter the full path to your music library"
    )

    if library_path and Path(library_path).exists():
        st.success(f"✓ Valid path: {library_path}")
        st.session_state.library_path = library_path

        if st.button("Next →", type="primary"):
            st.session_state.cleanup_step = 2
            st.rerun()
    else:
        st.error("⚠ Path does not exist. Please enter a valid directory path.")


def render_cleanup_step2():
    """Step 2: Scan mode selection"""
    st.subheader("Step 2: Select Scan Mode")

    scan_mode = st.radio(
        "Choose scan mode:",
        options=['quick', 'deep', 'custom'],
        format_func=lambda x: {
            'quick': '⚡ Quick Scan - Fast metadata-based detection (Speed: ★★★★★, Accuracy: ★★★☆☆)',
            'deep': '🔍 Deep Scan - Content hash + metadata analysis (Speed: ★★★☆☆, Accuracy: ★★★★★)',
            'custom': '⚙️ Custom Scan - Configure parameters (Speed: Variable, Accuracy: Variable)'
        }[x],
        index=1  # Default to deep scan
    )

    st.session_state.scan_mode = scan_mode

    # Custom mode configuration
    if scan_mode == 'custom':
        st.markdown("#### Custom Configuration")
        col1, col2 = st.columns(2)

        with col1:
            use_content_hash = st.checkbox("Use content hash matching", value=True)
            st.session_state.use_content_hash = use_content_hash

        with col2:
            fuzzy_threshold = st.slider(
                "Fuzzy match threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.85,
                step=0.05
            )
            st.session_state.fuzzy_threshold = fuzzy_threshold

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back"):
            st.session_state.cleanup_step = 1
            st.rerun()
    with col2:
        if st.button("Start Scan →", type="primary"):
            st.session_state.cleanup_step = 3
            st.rerun()


def render_cleanup_step3():
    """Step 3: Scanning progress"""
    st.subheader("Step 3: Scanning for Duplicates")

    db = get_library_db()
    if not db:
        st.error("Database connection failed. Please check settings.")
        return

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Get all files from database
        status_text.text("Loading files from database...")
        all_files = db.get_all_files()
        total_files = len(all_files)
        progress_bar.progress(0.2)

        status_text.text(f"Grouping {total_files:,} files by metadata...")

        # Group by metadata hash
        hash_groups = {}
        for file in all_files:
            if file.metadata_hash:
                hash_groups.setdefault(file.metadata_hash, []).append(file)

        progress_bar.progress(0.5)

        # Filter groups with duplicates
        duplicate_hash_groups = {k: v for k, v in hash_groups.items() if len(v) > 1}
        status_text.text(f"Analyzing quality for {len(duplicate_hash_groups):,} duplicate groups...")

        duplicate_groups = []
        for idx, (hash_key, files) in enumerate(duplicate_hash_groups.items()):
            # Extract quality metadata
            files_metadata = []
            for lib_file in files:
                metadata = extract_audio_metadata(lib_file.file_path)
                if metadata:
                    files_metadata.append(metadata)

            if len(files_metadata) > 1:
                keep, delete = rank_duplicate_group(files_metadata)

                duplicate_groups.append({
                    'group_id': f"dup_{len(duplicate_groups) + 1:04d}",
                    'files': files_metadata,
                    'keep': keep,
                    'delete': delete,
                    'space_savings_mb': sum(f.file_size for f in delete) / (1024 * 1024)
                })

            # Update progress
            progress_bar.progress(0.5 + (0.5 * (idx + 1) / len(duplicate_hash_groups)))

        progress_bar.progress(1.0)
        status_text.text("Scan complete!")

        # Store results in session state
        st.session_state.duplicate_groups = duplicate_groups
        st.session_state.scan_results = {
            'total_files': total_files,
            'duplicate_groups': len(duplicate_groups),
            'total_duplicates': sum(len(g['delete']) for g in duplicate_groups)
        }

        # Display summary
        st.success(f"✓ Scan Complete: Found {len(duplicate_groups)} duplicate groups")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Files Scanned", f"{total_files:,}")
        with col2:
            st.metric("Duplicate Groups", len(duplicate_groups))
        with col3:
            total_space = sum(g['space_savings_mb'] for g in duplicate_groups)
            st.metric("Potential Space Savings", f"{total_space:.2f} MB")

        if duplicate_groups:
            if st.button("Review Duplicates →", type="primary"):
                st.session_state.cleanup_step = 4
                st.rerun()
        else:
            st.info("No duplicates found! Your library is clean.")
            if st.button("Return to Dashboard"):
                st.session_state.cleanup_step = 1
                st.rerun()

    except Exception as e:
        st.error(f"Error during scan: {e}")
        logger.error(f"Scan error: {e}", exc_info=True)


def render_cleanup_step4():
    """Step 4: Review duplicates with side-by-side comparison"""
    st.subheader("Step 4: Review Duplicate Groups")

    duplicate_groups = st.session_state.duplicate_groups

    if not duplicate_groups:
        st.warning("No duplicate groups to review.")
        return

    st.info(f"Review {len(duplicate_groups)} duplicate groups. Select which files to delete.")

    # Display each group in expander
    for idx, group in enumerate(duplicate_groups):
        with st.expander(f"Group {idx + 1}/{len(duplicate_groups)} - {group['group_id']}", expanded=(idx < 3)):
            # Create comparison table
            comparison_data = []

            # Add keep file
            keep = group['keep']
            comparison_data.append({
                'Action': '✅ KEEP',
                'File': Path(keep.filepath).name,
                'Format': keep.format.upper(),
                'Quality': f"{keep.quality_score}/100",
                'Size (MB)': f"{keep.file_size / (1024*1024):.1f}",
                'Bitrate': f"{keep.bitrate or 'N/A'} kbps"
            })

            # Add delete files
            for file in group['delete']:
                comparison_data.append({
                    'Action': '❌ DELETE',
                    'File': Path(file.filepath).name,
                    'Format': file.format.upper(),
                    'Quality': f"{file.quality_score}/100",
                    'Size (MB)': f"{file.file_size / (1024*1024):.1f}",
                    'Bitrate': f"{file.bitrate or 'N/A'} kbps"
                })

            df = pd.DataFrame(comparison_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown(f"**Space to free:** {group['space_savings_mb']:.2f} MB")

            # Confirmation checkbox
            confirm_key = f"confirm_{group['group_id']}"
            confirmed = st.checkbox(
                f"Confirm deletion for group {idx + 1}",
                key=confirm_key,
                value=group['group_id'] in st.session_state.confirmed_groups
            )

            if confirmed:
                st.session_state.confirmed_groups.add(group['group_id'])
            else:
                st.session_state.confirmed_groups.discard(group['group_id'])

    # Navigation
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back"):
            st.session_state.cleanup_step = 2
            st.rerun()
    with col2:
        confirmed_count = len(st.session_state.confirmed_groups)
        if st.button(f"Next ({confirmed_count} groups selected) →", type="primary", disabled=confirmed_count == 0):
            st.session_state.cleanup_step = 5
            st.rerun()


def render_cleanup_step5():
    """Step 5: Quality distribution and summary"""
    st.subheader("Step 5: Deletion Summary")

    duplicate_groups = st.session_state.duplicate_groups
    confirmed_groups = [g for g in duplicate_groups if g['group_id'] in st.session_state.confirmed_groups]

    if not confirmed_groups:
        st.warning("No groups confirmed for deletion.")
        return

    # Summary metrics
    total_files_to_delete = sum(len(g['delete']) for g in confirmed_groups)
    total_space_to_free = sum(g['space_savings_mb'] for g in confirmed_groups)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Groups to Process", len(confirmed_groups))
    with col2:
        st.metric("Files to Delete", total_files_to_delete)
    with col3:
        st.metric("Space to Free", f"{total_space_to_free:.2f} MB")

    st.markdown("---")

    # Quality distribution chart
    st.subheader("Quality Distribution of Files to Delete")

    quality_tiers = {'Excellent': 0, 'Good': 0, 'Fair': 0, 'Poor': 0}
    for group in confirmed_groups:
        for file in group['delete']:
            tier = get_quality_tier(file.quality_score)
            quality_tiers[tier] = quality_tiers.get(tier, 0) + 1

    fig = go.Figure(data=[
        go.Bar(
            x=list(quality_tiers.keys()),
            y=list(quality_tiers.values()),
            marker_color=[COLORS['success'], COLORS['spotify_green'], COLORS['warning'], COLORS['error']]
        )
    ])
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color=COLORS['text_primary'],
        xaxis_title="Quality Tier",
        yaxis_title="Number of Files"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Navigation
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back"):
            st.session_state.cleanup_step = 4
            st.rerun()
    with col2:
        if st.button("Proceed to Confirmation →", type="primary"):
            st.session_state.cleanup_step = 6
            st.rerun()


def render_cleanup_step6():
    """Step 6: Final confirmation with safety checks"""
    st.subheader("Step 6: Final Confirmation")

    st.warning("⚠️ **Safety Checkpoint** - This action will permanently delete files.")
    st.info("A backup will be created before deletion.")

    confirmed_groups = [g for g in st.session_state.duplicate_groups if g['group_id'] in st.session_state.confirmed_groups]
    total_files = sum(len(g['delete']) for g in confirmed_groups)

    st.markdown(f"**Files to delete:** {total_files}")
    st.markdown(f"**Groups:** {len(confirmed_groups)}")

    # Confirmation input
    st.markdown("---")
    confirmation_phrase = "DELETE DUPLICATES"
    user_input = st.text_input(
        f"Type '{confirmation_phrase}' to confirm:",
        type="default"
    )

    confirmation_checkbox = st.checkbox("I understand this action cannot be undone")

    # Navigation
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back"):
            st.session_state.cleanup_step = 5
            st.rerun()
    with col2:
        can_proceed = (user_input == confirmation_phrase) and confirmation_checkbox
        if st.button("Execute Deletion →", type="primary", disabled=not can_proceed):
            st.session_state.cleanup_step = 7
            st.rerun()


def render_cleanup_step7():
    """Step 7: Execute deletion"""
    st.subheader("Step 7: Executing Cleanup")

    progress_bar = st.progress(0)
    status_text = st.empty()

    confirmed_groups = [g for g in st.session_state.duplicate_groups if g['group_id'] in st.session_state.confirmed_groups]

    try:
        # Create deletion plan
        status_text.text("Creating deletion plan...")
        backup_dir = Path(st.session_state.library_path) / '.cleanup_backups'
        deletion_plan = SafeDeletionPlan(backup_dir=str(backup_dir))

        for group in confirmed_groups:
            deletion_plan.add_group(
                keep_file=group['keep'].filepath,
                delete_files=[f.filepath for f in group['delete']],
                reason=f"Duplicate group {group['group_id']}"
            )

        progress_bar.progress(0.2)

        # Validate plan
        status_text.text("Validating deletion plan...")
        is_valid, errors = deletion_plan.validate()

        if not is_valid:
            st.error("Validation failed:\n" + "\n".join(errors))
            return

        progress_bar.progress(0.4)

        # Execute deletion
        status_text.text("Creating backups and deleting files...")
        with st.spinner("Deleting files..."):
            deletion_stats = deletion_plan.execute(dry_run=False, create_backup=True)

        progress_bar.progress(1.0)
        status_text.text("Cleanup complete!")

        # Store stats
        st.session_state.deletion_stats = deletion_stats

        # Show results
        st.success(f"✓ Successfully deleted {deletion_stats.files_deleted} files")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Files Deleted", deletion_stats.files_deleted)
        with col2:
            st.metric("Space Freed", f"{deletion_stats.space_freed_bytes / (1024*1024):.2f} MB")
        with col3:
            st.metric("Groups Processed", deletion_stats.successful_deletions)

        if st.button("View Summary →", type="primary"):
            st.session_state.cleanup_step = 8
            st.rerun()

    except Exception as e:
        st.error(f"Error during cleanup: {e}")
        logger.error(f"Cleanup error: {e}", exc_info=True)


def render_cleanup_step8():
    """Step 8: Completion summary"""
    st.subheader("Step 8: Cleanup Complete! 🎉")

    st.balloons()

    deletion_stats = st.session_state.get('deletion_stats')

    if deletion_stats:
        st.success("Smart Cleanup completed successfully!")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Files Deleted", deletion_stats.files_deleted)
        with col2:
            st.metric("Space Freed", f"{deletion_stats.space_freed_bytes / (1024*1024):.2f} MB")
        with col3:
            st.metric("Successful Groups", deletion_stats.successful_deletions)
        with col4:
            st.metric("Failed Operations", deletion_stats.failed_deletions)

        # Backup info
        if deletion_stats.backup_created:
            st.info(f"📦 Backup created at: {deletion_stats.backup_path}")

        # Export reports
        if st.button("Export Detailed Report"):
            # Generate report
            report_data = {
                'session_id': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'timestamp': datetime.now().isoformat(),
                'statistics': deletion_stats.to_dict()
            }

            report_json = json.dumps(report_data, indent=2)
            st.download_button(
                label="Download JSON Report",
                data=report_json,
                file_name=f"cleanup_report_{report_data['session_id']}.json",
                mime="application/json"
            )

    # Reset button
    if st.button("Start New Cleanup", type="primary"):
        st.session_state.cleanup_step = 1
        st.session_state.confirmed_groups = set()
        st.session_state.duplicate_groups = []
        st.rerun()


# ============================================================================
# LIBRARY STATS PAGE
# ============================================================================

def render_library_stats():
    """Render detailed library statistics and analytics"""
    st.title("📊 Library Statistics")

    db = get_library_db()
    if not db:
        st.info("Configure your library path in Settings to view statistics.")
        return

    try:
        stats = db.get_statistics()
    except Exception as e:
        st.error(f"Error loading statistics: {e}")
        return

    # Overview metrics
    st.subheader("📈 Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Files", f"{stats.total_files:,}")
    with col2:
        st.metric("Total Artists", f"{stats.artists_count:,}")
    with col3:
        st.metric("Library Size", f"{stats.total_size_gb:.2f} GB")
    with col4:
        avg_bitrate = stats.avg_bitrate or 0
        st.metric("Avg Bitrate", f"{avg_bitrate:.0f} kbps")

    st.markdown("---")

    # Format distribution
    st.subheader("🎵 Format Distribution")

    if stats.formats_breakdown:
        formats_df = pd.DataFrame([
            {'Format': fmt.upper(), 'Count': count, 'Percentage': f"{(count / stats.total_files * 100):.1f}%"}
            for fmt, count in sorted(stats.formats_breakdown.items(), key=lambda x: x[1], reverse=True)
        ])

        col1, col2 = st.columns([1, 1])

        with col1:
            # Pie chart
            fig = px.pie(
                formats_df,
                values='Count',
                names='Format',
                title='Format Distribution'
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color=COLORS['text_primary']
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Table
            st.dataframe(formats_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Bitrate distribution
    st.subheader("🎚️ Bitrate Distribution")

    # Mock bitrate data - replace with actual DB query
    bitrate_ranges = {
        '< 128 kbps': 120,
        '128-192 kbps': 340,
        '192-256 kbps': 580,
        '256-320 kbps': 920,
        '> 320 kbps (Lossless)': 440
    }

    fig = go.Figure(data=[
        go.Bar(
            x=list(bitrate_ranges.keys()),
            y=list(bitrate_ranges.values()),
            marker_color=COLORS['spotify_green']
        )
    ])
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color=COLORS['text_primary'],
        xaxis_title="Bitrate Range",
        yaxis_title="Number of Files"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Quality tier breakdown
    st.subheader("⭐ Quality Tier Breakdown")

    quality_tiers = {
        'Excellent (80-100)': 850,
        'Good (60-79)': 720,
        'Fair (40-59)': 340,
        'Poor (0-39)': 90
    }

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            x=list(quality_tiers.values()),
            y=list(quality_tiers.keys()),
            orientation='h',
            color=list(quality_tiers.values()),
            color_continuous_scale=['red', 'orange', 'yellow', 'green']
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color=COLORS['text_primary'],
            xaxis_title="Number of Files",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        for tier, count in quality_tiers.items():
            percentage = (count / sum(quality_tiers.values()) * 100)
            st.metric(tier, f"{count:,}", f"{percentage:.1f}%")


# ============================================================================
# SETTINGS PAGE
# ============================================================================

def render_settings():
    """Render settings and configuration page"""
    st.title("⚙️ Settings")

    # Database Configuration
    st.subheader("💾 Database Configuration")

    db_path = st.text_input(
        "Database Path",
        value=st.session_state.db_path,
        help="Path to the SQLite database file"
    )

    if db_path != st.session_state.db_path:
        if Path(db_path).exists() or st.checkbox("Create new database at this path"):
            st.session_state.db_path = db_path
            st.success("Database path updated!")

    st.markdown("---")

    # Spotify Configuration
    st.subheader("🟢 Spotify Configuration")

    spotify_client_id = st.text_input(
        "Spotify Client ID",
        type="password",
        help="Your Spotify API client ID"
    )

    spotify_client_secret = st.text_input(
        "Spotify Client Secret",
        type="password",
        help="Your Spotify API client secret"
    )

    if st.button("Save Spotify Config"):
        # Save to config file
        config_dir = Path.home() / '.music_tools'
        config_dir.mkdir(exist_ok=True)

        config_file = config_dir / 'spotify_config.json'
        config_data = {
            'client_id': spotify_client_id,
            'client_secret': spotify_client_secret
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        st.success("Spotify configuration saved!")

    st.markdown("---")

    # Deezer Configuration
    st.subheader("🟠 Deezer Configuration")

    deezer_email = st.text_input(
        "Deezer Email",
        help="Your Deezer account email"
    )

    if st.button("Save Deezer Config"):
        config_dir = Path.home() / '.music_tools'
        config_dir.mkdir(exist_ok=True)

        config_file = config_dir / 'deezer_config.json'
        config_data = {
            'email': deezer_email
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        st.success("Deezer configuration saved!")

    st.markdown("---")

    # Smart Cleanup Preferences
    st.subheader("🧹 Smart Cleanup Preferences")

    default_scan_mode = st.selectbox(
        "Default Scan Mode",
        options=['quick', 'deep', 'custom'],
        format_func=lambda x: {'quick': 'Quick Scan', 'deep': 'Deep Scan', 'custom': 'Custom Scan'}[x],
        index=1
    )

    auto_backup = st.checkbox("Always create backup before deletion", value=True)

    backup_retention_days = st.number_input(
        "Backup Retention (days)",
        min_value=1,
        max_value=365,
        value=30,
        help="Number of days to keep backup files"
    )

    if st.button("Save Preferences"):
        preferences = {
            'default_scan_mode': default_scan_mode,
            'auto_backup': auto_backup,
            'backup_retention_days': backup_retention_days
        }

        config_dir = Path.home() / '.music_tools'
        config_dir.mkdir(exist_ok=True)

        config_file = config_dir / 'preferences.json'
        with open(config_file, 'w') as f:
            json.dump(preferences, f)

        st.success("Preferences saved!")


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main application entry point"""

    # Initialize session state
    init_session_state()

    # Sidebar navigation
    st.sidebar.title("🎵 Music Tools")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        options=["Dashboard", "Smart Cleanup", "Library Stats", "Settings"],
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Info")
    st.sidebar.info(f"**Library:** {Path(st.session_state.library_path).name}")
    st.sidebar.info(f"**Database:** {Path(st.session_state.db_path).name}")

    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### About
    **Music Tools** v1.0.0

    Modern web interface for music library management.

    Features:
    - Library statistics
    - Smart duplicate cleanup
    - Quality analysis
    - Spotify/Deezer integration
    """)

    # Render selected page
    if page == "Dashboard":
        render_dashboard()
    elif page == "Smart Cleanup":
        render_smart_cleanup()
    elif page == "Library Stats":
        render_library_stats()
    elif page == "Settings":
        render_settings()


if __name__ == "__main__":
    main()
