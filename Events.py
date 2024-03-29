import math
from abc import ABC

import otf2.definitions
import constants


class Event(ABC):

    def __init__(self, rank_id, function, start_time, end_time, level, tid):
        self.rank_id = rank_id
        self.function = function
        self.start_time = start_time
        self.end_time = end_time
        self.level = level
        self.tid = tid
        self.paradigm = None

        # set paradigm
        if "MPI_" in function:
            self.paradigm = "MPI"
        elif "H5" in function:
            self.paradigm = "HDF5"
        elif function in ["creat", "creat64", "open", "open64", "close", "read", "write", "pread", "pwrite", "pread64", "pwrite64", "readv", "writev", "lseek", "lseek64", "unlink", "getcwd", "umask", "fcntl"]:
            self.paradigm = "POSIX"
        elif function in ["fopen", "fopen64", "fseek", "fread", "fwrite", "ftell", "fsync", "fdatasync", "fctrl", "dup", "dup2", "fdopen", "fseeko", "ftello"]:
            self.paradigm = "ISOC"

    def get_start_time_ticks(self, timer_resolution):
        return math.ceil(self.start_time*timer_resolution)

    def get_end_time_ticks(self, timer_resolution):
        return math.ceil(self.end_time*timer_resolution)

    @classmethod
    def get_event(cls, rank_id, function, start_time, end_time, level, tid, args):

        if function in ["creat", "creat64", "open", "open64", "fopen", "fopen64", "fdopen"]:
            return IoCreateHandleEvent(rank_id, function, start_time, end_time, level, tid, args)
        elif function in ["close", "fclose"]:
            return IoDestroyHandleEvent(rank_id, function, start_time, end_time, level, tid, args)
        elif function in ["read", "write", "pread", "pwrite", "pread64", "pwrite64", "readv", "writev", "fread", "fwrite"]:
            return IoEvent(rank_id, function, start_time, end_time, level, tid, args)
        elif function in ["lseek", "lseek64", "fseek", "fseeko"]:
            return IoSeekEvent(rank_id, function, start_time, end_time, level, tid, args)
        else:
            return PlaceholderEvent(rank_id, function, start_time, end_time, level, tid, args)

    def __repr__(self):
        return f"{self.start_time} : {self.function}"


class IoCreateHandleEvent(Event):

    def __init__(self, rank_id, function, start_time, end_time, level, tid, args):
        super(IoCreateHandleEvent, self).__init__(rank_id, function, start_time, end_time, level, tid)

        self.path_name = None

        self.mode = None
        self.status = []
        self.creation = []

        # posix
        if self.paradigm == "POSIX":

            self.path_name = args[0].decode("utf-8")
            self.flags = int(args[1].decode("utf-8"))

            # io mode

            if constants.check_flag(self.flags, constants.O_WRONLY):
                self.mode = otf2.IoAccessMode.WRITE_ONLY.value
            elif constants.check_flag(self.flags, constants.O_RDWR):
                self.mode = otf2.IoAccessMode.READ_WRITE.value
            else:
                self.mode = otf2.IoAccessMode.READ_ONLY.value

            # creation flags

            if constants.check_flag(self.flags, constants.O_CREAT):
                self.creation.append(otf2.IoCreationFlag.CREATE.value)

            if constants.check_flag(self.flags, constants.O_TRUNC):
                self.creation.append(otf2.IoCreationFlag.TRUNCATE.value)

            # directory missing

            if constants.check_flag(self.flags, constants.O_EXCL):
                self.creation.append(otf2.IoCreationFlag.EXCLUSIVE.value)

            if constants.check_flag(self.flags, constants.O_NOCTTY):
                self.creation.append(otf2.IoCreationFlag.NO_CONTROLLING_TERMINAL.value)

            if constants.check_flag(self.flags, constants.O_NOFOLLOW):
                self.creation.append(otf2.IoCreationFlag.NO_FOLLOW.value)

            # path missing
            # temporary_file missing
            # large file not implemented/not working in otf2 -> __O_LARGEFILE does nothing
            # no_seek missing
            # unique missing

            # status flags

            if constants.check_flag(self.flags, constants.O_CLOEXEC):
                self.status.append(otf2.IoStatusFlag.CLOSE_ON_EXEC.value)

            if constants.check_flag(self.flags, constants.O_APPEND):
                self.creation.append(otf2.IoStatusFlag.APPEND.value)

            if constants.check_flag(self.flags, constants.O_NONBLOCK):
                self.status.append(otf2.IoStatusFlag.NON_BLOCKING.value)

            if constants.check_flag(self.flags, constants.FASYNC):
                self.status.append(otf2.IoStatusFlag.ASYNC.value)

            # sync missing
            # data_sync missing

            if constants.check_flag(self.flags, constants.O_DIRECT):
                self.status.append(otf2.IoStatusFlag.AVOID_CACHING.value)

            if constants.check_flag(self.flags, constants.O_NOATIME):
                self.status.append(otf2.IoStatusFlag.NO_ACCESS_TIME.value)

        # isoc
        if self.paradigm == "ISOC":

            self.path_name = args[0].decode("utf-8")
            self.mode = args[1].decode("utf-8")
            if self.mode in ["r"]:
                self.mode = otf2.IoAccessMode.READ_ONLY.value
            elif self.mode in ["w", "a"]:
                self.mode = otf2.IoAccessMode.WRITE_ONLY.value
            elif self.mode in ["r+", "w+", "a+"]:
                self.mode = otf2.IoAccessMode.READ_WRITE.value

        if len(self.status) == 0:
            self.status.append(otf2.IoStatusFlag.NONE.value)

        if len(self.creation) == 0:
            self.creation.append(otf2.IoCreationFlag.NONE.value)


class IoDestroyHandleEvent(Event):

    def __init__(self, rank_id, function, start_time, end_time, level, tid, args):
        super(IoDestroyHandleEvent, self).__init__(rank_id, function, start_time, end_time, level, tid)

        if function in ["close", "fclose"]:

            self.path_name = args[0].decode("utf-8")


class IoDuplicateHandleEvent(Event):

    def __init__(self, rank_id, function, start_time, end_time, level, tid):
        super(IoDuplicateHandleEvent, self).__init__(rank_id, function, start_time, end_time, level, tid)


class IoDeleteFileEvent(Event):
    def __init__(self, rank_id, function, start_time, end_time, level, tid):
        super(IoDeleteFileEvent, self).__init__(rank_id, function, start_time, end_time, level, tid)


class IoEvent(Event):

    def __init__(self, rank_id, function, start_time, end_time, level, tid, args):
        super(IoEvent, self).__init__(rank_id, function, start_time, end_time, level, tid)

        self.offset = None
        self.num_chunks = 1

        if function in ["write", "pwrite", "pwrite64", "writev", "fwrite"]:
            self.type = otf2.IoOperationMode.WRITE.value

        if function in ["read", "pread", "pread64", "readv", "fread"]:
            self.type = otf2.IoOperationMode.READ.value

        if function in ["read", "write"]:
            self.path_name = args[0].decode("utf-8")
            self.size = int(args[2].decode("utf-8"))

        if function in ["readv", "writev"]:
            self.path_name = args[0].decode("utf-8")
            self.size = int(args[1].decode("utf-8"))
            self.num_chunks = int(args[2].decode("utf-8"))

        if function in ["fread", "fwrite"]:

            self.size = int(args[1].decode("utf-8")) * int(args[2].decode("utf-8"))
            self.path_name = args[3].decode("utf-8")

        if function in ["pread", "pwrite", "pread64", "pwrite64"]:
            self.offset = int(args[3].decode("utf-8"))
            self.path_name = args[0].decode("utf-8")
            self.size = int(args[2].decode("utf-8"))


# scorep_posix_io_wrap.c
class IoSeekEvent(Event):

    def __init__(self, rank_id, function, start_time, end_time, level, tid, args):
        super(IoSeekEvent, self).__init__(rank_id, function, start_time, end_time, level, tid)

        if function in ["lseek", "lseek64", "fseek"]:
            self.paradigm = "POSIX"
            self.path_name = args[0].decode("utf-8")
            self.offset = int(args[1].decode("utf-8"))
            self.whence = int(args[2].decode("utf-8"))


class PlaceholderEvent(Event):

    def __init__(self, rank_id, function, start_time, end_time, level, tid, args):
        super(PlaceholderEvent, self).__init__(rank_id, function, start_time, end_time, level, tid)
        #print(args)


# #creat
# #creat64
# #open
# #open64
# #close
# #write
# #read
# #lseek
# #lseek64
# #pread
# #pread64
# #pwrite
# #pwrite64
# #readv
# #writev
# mmap
# mmap64
# #fopen
# #fopen64
# #fclose
# #fwrite
# #fread
# ftell
# #fseek
# fsync
# fdatasync
# __xstat
# __xstat64
# __lxstat
# __lxstat64
# __fxstat
# __fxstat64
# getcwd
# mkdir
# rmdir
# chdir
# link
# linkat
# unlink
# symlink
# symlinkat
# readlink
# readlinkat
# rename
# chmod
# chown
# lchown
# utime
# opendir
# readdir
# closedir
# rewinddir
# mknod
# mknodat
# fcntl
# dup
# dup2
# pipe
# mkfifo
# umask
# fdopen
# fileno
# access
# faccessat
# tmpfile
# remove
# truncate
# ftruncate
# vfprintf
# msync
# fseeko
# ftello




# MPI_File_close
# MPI_File_set_size
# MPI_File_iread_at
# MPI_File_iread
# MPI_File_iread_shared
# MPI_File_iwrite_at
# MPI_File_iwrite
# MPI_File_iwrite_shared
# MPI_File_open
# MPI_File_read_all_begin
# MPI_File_read_all
# MPI_File_read_at_all
# MPI_File_read_at_all_begin
# MPI_File_read_at
# MPI_File_read
# MPI_File_read_ordered_begin
# MPI_File_read_ordered
# MPI_File_read_shared
# MPI_File_set_view
# MPI_File_sync
# MPI_File_write_all_begin
# MPI_File_write_all
# MPI_File_write_at_all_begin
# MPI_File_write_at_all
# MPI_File_write_at
# MPI_File_write
# MPI_File_write_ordered_begin
# MPI_File_write_ordered
# MPI_File_write_shared
# MPI_Finalize
# MPI_Finalized
# MPI_Init
# MPI_Init_thread
# MPI_Wtime
# MPI_Comm_rank
# MPI_Comm_size
# MPI_Get_processor_name
# MPI_Get_processor_name
# MPI_Comm_set_errhandler
# MPI_Barrier
# MPI_Bcast
# MPI_Gather
# MPI_Gatherv
# MPI_Scatter
# MPI_Scatterv
# MPI_Allgather
# MPI_Allgatherv
# MPI_Alltoall
# MPI_Reduce
# MPI_Allreduce
# MPI_Reduce_scatter
# MPI_Scan
# MPI_Type_commit
# MPI_Type_contiguous
# MPI_Type_extent
# MPI_Type_free
# MPI_Type_hindexed
# MPI_Op_create
# MPI_Op_free
# MPI_Type_get_envelope
# MPI_Type_size
# MPI_Cart_rank
# MPI_Cart_create
# MPI_Cart_get
# MPI_Cart_shift
# MPI_Wait
# MPI_Send
# MPI_Recv
# MPI_Sendrecv
# MPI_Isend
# MPI_Irecv
# MPI_Info_create
# MPI_Info_set
# MPI_Info_get
# MPI_Waitall
# MPI_Waitsome
# MPI_Waitany
# MPI_Ssend
# MPI_Comm_split
# MPI_Comm_dup
# MPI_Comm_create
# MPI_File_seek
# MPI_File_seek_shared
# MPI_File_get_size
# MPI_Ibcast
# MPI_Test
# MPI_Testall
# MPI_Testsome
# MPI_Testany
# MPI_Ireduce
# MPI_Iscatter
# MPI_Igather
# MPI_Ialltoall
# MPI_Comm_free
# MPI_Cart_sub
# MPI_Comm_split_type
# H5Fcreate
# H5Fopen
# H5Fclose
# H5Fflush
# H5Gclose
# H5Gcreate1
# H5Gcreate2
# H5Gget_objinfo
# H5Giterate
# H5Gopen1
# H5Gopen2
# H5Dclose
# H5Dcreate1
# H5Dcreate2
# H5Dget_create_plist
# H5Dget_space
# H5Dget_type
# H5Dopen1
# H5Dopen2
# H5Dread
# H5Dwrite
# H5Dset_extent
# H5Sclose
# H5Screate
# H5Screate_simple
# H5Sget_select_npoints
# H5Sget_simple_extent_dims
# H5Sget_simple_extent_npoints
# H5Sselect_elements
# H5Sselect_hyperslab
# H5Sselect_none
# H5Tclose
# H5Tcopy
# H5Tget_class
# H5Tget_size
# H5Tset_size
# H5Tcreate
# H5Tinsert
# H5Aclose
# H5Acreate1
# H5Acreate2
# H5Aget_name
# H5Aget_num_attrs
# H5Aget_space
# H5Aget_type
# H5Aopen
# H5Aopen_idx
# H5Aopen_name
# H5Aread
# H5Awrite
# H5Pclose
# H5Pcreate
# H5Pget_chunk
# H5Pget_mdc_config
# H5Pset_alignment
# H5Pset_chunk
# H5Pset_dxpl_mpio
# H5Pset_fapl_core
# H5Pset_fapl_mpio
# H5Pset_fapl_mpiposix
# H5Pset_istore_k
# H5Pset_mdc_config
# H5Pset_meta_block_size
# H5Lexists
# H5Lget_val
# H5Literate
# H5Oclose
# H5Oget_info
# H5Oget_info_by_name
# H5Oopen
# H5Pset_coll_metadata_write
# H5Pget_coll_metadata_write
# H5Pset_all_coll_metadata_ops
# H5Pget_all_coll_metadata_ops
