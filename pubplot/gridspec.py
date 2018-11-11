#!/usr/bin/env python3
import numpy as np
import matplotlib.gridspec as mgridspec
from .rcmod import rc
from .utils import dot_dict
ifNone = lambda x,y: x if x is not None else y

# Custom settings for various journals
# Add to this throughout your career, or as standards change
# PNAS info: http://www.pnas.org/page/authors/submission
# AMS info: https://www.ametsoc.org/ams/index.cfm/publications/authors/journal-and-bams-authors/figure-information-for-authors/
# AGU info: https://publications.agu.org/author-resource-center/figures-faq/
def journalsize(width, height):
    # User wants to define their own size
    if type(width) is not str:
        return width, height
    # Determine automatically
    table = {
        'pnas1': 8.7*cm2in,
        'pnas2': 11.4*cm2in,
        'pnas3': 17.8*cm2in,
        'ams1': 3.2,
        'ams2': 4.5,
        'ams3': 5.5,
        'ams4': 6.5,
        'agu1': (95*mm2in, 115*mm2in),
        'agu2': (190*mm2in, 115*mm2in),
        'agu3': (95*mm2in, 230*mm2in),
        'agu4': (190*mm2in, 230*mm2in),
        }
    value = table.get(width, None)
    if value is None:
        raise ValueError(f'Unknown journal figure width specifier "{width}". ' +
                          'Options are: ' + ', '.join(table.keys()))
    # Output width, and optionally also specify height
    if utils.isnumber(value):
        width = value
    else:
        width, height = value
    return width, height

# Function for processing input and generating necessary keyword args
def _gridspec_kwargs(array=None, rowmajor=True, # mode 1: specify everything with array
    autonumber=False,
    nrows=1, ncols=1, emptycols=None, emptyrows=None, # mode 2: use convenient kwargs for simple grids
    aspect=1,    height=None, width=None,   # for controlling aspect ratio, default is control for width
    hspace=None, wspace=None, hratios=None, wratios=None, # spacing between axes, in inches (hspace should be bigger, allowed room for title)
    left=None,   bottom=None, right=None,   top=None,     # spaces around edge of main plotting area, in inches
    bwidth=None, bspace=None, rwidth=None, rspace=None, lwidth=None, lspace=None, # default to no space between panels
    bottompanel=False, bottompanels=False, # bottompanelrows=1, # optionally draw extra rows
    rightpanel=False,  rightpanels=False,  # rightpanelcols=1,
    leftpanel=False,   leftpanels=False,   # leftpanelcols=1,
    bottomcolorbar=False, bottomcolorbars=False, bottomlegend=False, bottomlegends=False, # convenient aliases that change default features
    rightcolorbar=False,  rightcolorbars=False,  rightlegend=False,  rightlegends=False,
    leftcolorbar=False,   leftcolorbars=False,   leftlegend=False,   leftlegends=False
    ):
    #--------------------------------------------------------------------------#
    # Parse complicated input
    #--------------------------------------------------------------------------#
    # Handle the convenience feature for specifying the desired width/spacing
    # for panels as that suitable for a colorbar or legend
    # NOTE: Ugly but this is mostly boilerplate, shouln't change much
    def _panelprops(panel, panels, colorbar, colorbars, legend, legends, width, space):
        if colorbar or colorbars:
            width = ifNone(width, rc.subplots['cbar'])
            space = ifNone(space, rc.subplots['labs'])
            panel, panels = colorbar, colorbars
        elif legend or legends:
            width = ifNone(width, rc.subplots['legend'])
            space = ifNone(space, 0)
            panel, panels = legend, legends
        return panel, panels, width, space
    rightpanel, rightpanels, rwidth, rspace, = _panelprops(
        rightpanel, rightpanels, rightcolorbar, rightcolorbars,
        rightlegend, rightlegends, rwidth, rspace)
    leftpanel, leftpanels, lwidth, lspace = _panelprops(
        leftpanel, leftpanels, leftcolorbar, leftcolorbars,
        leftlegend, leftlegends, lwidth, lspace)
    bottompanel, bottompanels, bwidth, bspace = _panelprops(
        bottompanel, bottompanels, bottomcolorbar, bottomcolorbars,
        bottomlegend, bottomlegends, bwidth, bspace)

    # Handle the convenience feature for generating one panel per row/column
    # and one single panel for all rows/columns
    def _parse(panel, panels, nmax):
        if panel: # one spanning panel
            panels = [1]*nmax
        elif panels not in (None,False): # can't test truthiness, want user to be allowed to pass numpy vector!
            try:
                panels = list(panels)
            except TypeError:
                panels = [*range(nmax)] # pass True to make panel for each column
        return panels
    bottompanels = _parse(bottompanel, bottompanels, ncols)
    rightpanels  = _parse(rightpanel,  rightpanels,  nrows)
    leftpanels   = _parse(leftpanel,   leftpanels,   nrows)
    row_offset = 0
    col_offset = 1 if leftpanels else 0

    # Array setup
    if array is None:
        array = np.arange(1,nrows*ncols+1)[...,None]
        order = 'C' if rowmajor else 'F' # for column major, use Fortran ordering
        array = array.reshape((nrows, ncols), order=order) # numpy is row-major, remember
    array = np.array(array) # enforce array type
    if array.ndim==1:
        array = array[None,:] if rowmajor else array[:,None] # interpret as single row or column
    # Empty rows/columns feature
    array[array==None] = 0 # use zero for placeholder; otherwise have issues
    if emptycols is not None:
        emptycols = np.atleast_1d(emptycols)
        for col in emptycols.flat:
            array[:,col-1] = 0
    if emptyrows is not None:
        emptyrows = np.atleast_1d(emptyrows)
        for row in emptyrows.flat:
            array[row-1,:] = 0
    # Optionally standardize numbering in array
    if autonumber:
        number = 1
        newarray = np.zeros(array.shape)
        for row in newarray.shape[0]:
            for col in newarray.shape[1]:
                if array[row,col] not in array.flat: # not already declared
                    newarray[array==array[row,col]] = number
                    number += 1
        array = newarray
    nrows = array.shape[0]
    ncols = array.shape[1]

    # Apply the general defaults
    # Need to do this after number of rows/columns figured out
    try:
        aspect = aspect[0]/aspect[1]
    except (IndexError,TypeError):
        pass # do nothing
    wratios = np.atleast_1d(ifNone(wratios, 1))
    hratios = np.atleast_1d(ifNone(hratios, 1))
    hspace = np.atleast_1d(ifNone(hspace, rc.subplots['title']))
    wspace = np.atleast_1d(ifNone(wspace, rc.subplots['inner']))
    if len(wratios)==1:
        wratios = np.repeat(wratios, (ncols,))
    if len(hratios)==1:
        hratios = np.repeat(hratios, (nrows,))
    if len(wspace)==1:
        wspace = np.repeat(wspace, (ncols-1,))
    if len(hspace)==1:
        hspace = np.repeat(hspace, (nrows-1,))
    left   = ifNone(left,   rc.subplots['labs'])
    bottom = ifNone(bottom, rc.subplots['labs'])
    right  = ifNone(right,  rc.subplots['nolabs'])
    top    = ifNone(top,    rc.subplots['title'])
    bwidth = ifNone(bwidth, rc.subplots['cbar'])
    rwidth = ifNone(rwidth, rc.subplots['cbar'])
    lwidth = ifNone(lwidth, rc.subplots['cbar'])
    bspace = ifNone(bspace, rc.subplots['labs'])
    rspace = ifNone(rspace, rc.subplots['labs'])
    lspace = ifNone(lspace, rc.subplots['labs'])

    # Necessary arguments to reconstruct this grid
    # Can follow some of the pre-processing
    subplots_kw = dot_dict(array=array, width=width, height=height, aspect=aspect,
        hspace=hspace, wspace=wspace,
        hratios=hratios, wratios=wratios,
        nrows=nrows,   ncols=ncols,
        bottompanels=bottompanels, leftpanels=leftpanels, rightpanels=rightpanels,
        left=left,     bottom=bottom, right=right,   top=top,
        bwidth=bwidth, bspace=bspace, rwidth=rwidth, rspace=rspace, lwidth=lwidth, lspace=lspace,
        )

    #--------------------------------------------------------------------------
    # Get necessary keyword arg inputs to FlexibleGridSpec
    #--------------------------------------------------------------------------
    # If width and height are not fixed, determine necessary width/height to
    # preserve the aspect ratio of specified plot
    if width is None and height is None:
        width = 5 # default behavior is use 1:1 axes, fixed width
    width, height = journalsize(width, height) # if user passed width=<string>, will use that journal size
    auto_width  = (width is None and height is not None)
    auto_height = (height is None and width is not None)
    aspect = aspect/(wratios[0]/np.mean(wratios)) # e.g. if 2 columns, 5:1 width ratio, change the 'average' aspect ratio
    aspect = aspect*(hratios[0]/np.mean(hratios))
    # TODO: Account for top-left axes occupying multiple subplot slots!
    # bpanel_width = 0
    # rpanel_width = 0
    # lpanel_width = 0
    bpanel_space = bwidth + bspace if bottompanels else 0
    rpanel_space = rwidth + rspace if rightpanels else 0
    lpanel_space = lwidth + lspace if leftpanels else 0
    # bpanel_width = bwidth if bottompanels else 0
    # rpanel_width = rwidth if rightpanels else 0
    # lpanel_width = lwidth if leftpanels else 0
    # bpanel_space = bspace if bottompanels else 0
    # rpanel_space = rspace if rightpanels else 0
    # lpanel_space = lspace if leftpanels else 0
    if width is not None:
        # axwidth_ave = (width + lpanel_width + rpanel_width - left - right - sum(wspace) - rpanel_space - lpanel_space)/ncols
        axwidth_ave = (width - left - right - sum(wspace) - rpanel_space - lpanel_space)/ncols
    if height is not None:
        axheight_ave = (height - top - bottom - sum(hspace) - bpanel_space)/nrows
    # Fix height and top-left axes aspect ratio
    if auto_width:
        axwidth_ave = axheight_ave*aspect
        width       = axwidth_ave*ncols + left + right + sum(wspace) + rpanel_space + lpanel_space
    # Fix width and top-left axes aspect ratio
    if auto_height:
        axheight_ave = axwidth_ave/aspect
        height       = axheight_ave*nrows + top + bottom + sum(hspace) + bpanel_space
    # Make sure the 'ratios' and 'spaces' are in physical units (we cast the
    # former to physical units), easier then to add stuff as below
    if axwidth_ave<0:
        raise ValueError("Not enough room for axes. Increase width, or reduce spacings 'left', 'right', or 'wspace'.")
    if axheight_ave<0:
        raise ValueError("Not enough room for axes. Increase height, or reduce spacings 'top', 'bottom', or 'hspace'.")
    wspace = wspace.tolist()
    hspace = hspace.tolist()
    wratios = (ncols*axwidth_ave*(wratios/sum(wratios))).tolist()
    hratios = (nrows*axheight_ave*(hratios/sum(hratios))).tolist()

    # Now add the outer panel considerations (idea is we have panels whose
    # widths/heights are *in inches*, and only allow the main subplots and
    # figure widhts/heights to warp to preserve aspect ratio)
    nrows += int(bool(bottompanels))
    ncols += int(bool(rightpanels)) + int(bool(leftpanels))
    if bottompanels: # the 'bottom' space actually goes between subplots and panel
        hratios = hratios + [bwidth] # easy
        hspace  = hspace + [bottom]
        bottom  = bspace
    if leftpanels:
        wratios = [lwidth] + wratios
        wspace  = [left] + wspace
        left    = lspace
    if rightpanels:
        wratios = wratios + [rwidth]
        wspace  = wspace + [right]
        right   = rspace
    # Scale stuff that gridspec needs to be scaled
    # Scale the boundaries for gridspec
    # NOTE: We *no longer* scale wspace/hspace because we expect it to
    # be in same scale as axes ratios, much easier that way and no drawback really
    bottom = bottom/height
    left   = left/width
    top    = 1-top/height
    right  = 1-right/width

    # Create gridspec for outer plotting regions (divides 'main area' from side panels)
    offset = (0, 1 if leftpanels else 0)
    figsize = (width, height)
    gridspec_kw = dict(
            nrows         = nrows,
            ncols         = ncols,
            left          = left,
            bottom        = bottom,
            right         = right, # unique spacing considerations
            top           = top, # so far no panels allowed here
            wspace        = wspace,
            hspace        = hspace,
            width_ratios  = wratios,
            height_ratios = hratios,
            ) # set wspace/hspace to match the top/bottom spaces
    return figsize, array, offset, subplots_kw, gridspec_kw

# Generate custom GridSpec classes that override the GridSpecBase
# __setitem__ method and the 'base' __init__ method
def flexible_gridspec_factory(base):
    class _GridSpec(base):
        """
        Generalization of builtin matplotlib GridSpec that allows for
        subplots with *arbitrary spacing*. Accomplishes this by designating certain
        rows and columns as *empty*.

        Further accepts all spacing arguments in *inches*.

        This allows for user-specified extra spacing, and for automatic adjustment
        of spacing depending on whether labels or ticklabels are overlapping. Will
        be added to figure class as auto_adjust() method or something.
        """
        def __init__(self, nrows, ncols, **kwargs):
            # Add these as attributes; want _spaces_as_ratios to be
            # self-contained, so it can be invoked on already instantiated
            # gridspec (see 'update')
            self._nrows_visible = nrows
            self._ncols_visible = ncols
            self._nrows = nrows*2-1
            self._ncols = ncols*2-1
            wratios, hratios, kwargs = self._spaces_as_ratios(**kwargs)
            return super().__init__(self._nrows, self._ncols,
                    hspace=0, wspace=0, # we implement these as invisible rows/columns
                    width_ratios=wratios,
                    height_ratios=hratios,
                    **kwargs,
                    )

        def __getitem__(self, key):
            # Magic obfuscation that renders the 'space' rows and columns
            # invisible. Note key will be tuple if multiple indices requested.
            def _normalize(key, size):
                if isinstance(key, slice):
                    start, stop, _ = key.indices(size)
                    if stop > start:
                        return start, stop - 1
                else:
                    if key < 0:
                        key += size
                    if 0 <= key < size:
                        return key, key
                raise IndexError(f"Invalid index: {key} with size {size}.")
            # SubplotSpec initialization will figure out the row/column
            # geometry of these two number automatically
            nrows, ncols = self._nrows, self._ncols
            nrows_visible, ncols_visible = self._nrows_visible, self._ncols_visible
            if isinstance(key, tuple):
                try:
                    k1, k2 = key
                except ValueError:
                    raise ValueError('Unrecognized subplot spec "{key}".')
                num1, num2 = np.ravel_multi_index(
                    [_normalize(k1, nrows_visible), _normalize(k2, ncols_visible)],
                    (nrows, ncols),
                    )
            else:
                num1, num2 = _normalize(key, nrows_visible * ncols_visible)
            # When you move to a new column that skips a 'hspace' and when you
            # move to a new row that skips a 'wspace' -- so, just multiply
            # the scalar indices by 2!
            def _adjust(n):
                if n<0:
                    return 2*(n+1) - 1 # want -1 to stay -1, -2 becomes -3, etc.
                else:
                    return n*2
            num1, num2 = _adjust(num1), _adjust(num2)
            return mgridspec.SubplotSpec(self, num1, num2)

        def _spaces_as_ratios(self, hspace=None, wspace=None, # spacing between axes
                hratios=None, wratios=None,
                height_ratios=None, width_ratios=None,
                **kwargs):
            # Parse flexible input
            nrows = self._nrows_visible
            ncols = self._ncols_visible
            hratios = ifNone(height_ratios, hratios)
            wratios = ifNone(width_ratios,  wratios)
            hratios = np.atleast_1d(ifNone(hratios, 1))
            wratios = np.atleast_1d(ifNone(wratios, 1))
            hspace = np.atleast_1d(ifNone(hspace, np.mean(hratios)*0.10)) # this is relative to axes
            wspace = np.atleast_1d(ifNone(wspace, np.mean(wratios)*0.10))
            if len(wspace)==1:
                wspace = np.repeat(wspace, (ncols-1,))
            if len(hspace)==1:
                hspace = np.repeat(hspace, (nrows-1,))

            # Verify input ratios and spacings
            # Translate height/width spacings, implement as extra columns/rows
            if len(hratios) != nrows:
                raise ValueError(f'Got {nrows} rows, but {len(hratios)} hratios.')
            if len(wratios) != ncols:
                raise ValueError(f'Got {ncols} columns, but {len(wratios)} wratios.')
            if ncols>1 and len(wspace) != ncols-1:
                raise ValueError(f'Require {ncols-1} width spacings for {ncols} columns, got {len(wspace)}.')
            if nrows>1 and len(hspace) != nrows-1:
                raise ValueError(f'Require {nrows-1} height spacings for {nrows} rows, got {len(hspace)}.')

            # Assign spacing as ratios
            wratios_final = [None]*self._ncols
            wratios_final[::2] = list(wratios)
            if self._ncols>1:
                wratios_final[1::2] = list(wspace)
            hratios_final = [None]*self._nrows
            hratios_final[::2] = list(hratios)
            if self._nrows>1:
                hratios_final[1::2] = list(hspace)
            return wratios_final, hratios_final, kwargs # bring extra kwargs back

        def update(self, **gridspec_kw):
            # Handle special hspace/wspace arguments, and just set the simple
            # left/right/top/bottom attributes
            wratios, hratios, edges_kw = self._spaces_as_ratios(**gridspec_kw)
            edges_kw = {key:value for key,value in edges_kw.items()
                if key not in ('nrows','ncols')} # cannot be changed
            self.set_width_ratios(wratios)
            self.set_height_ratios(hratios)
            super().update(**edges_kw) # should just be left/right/top/bottom

    return _GridSpec

# Make classes
FlexibleGridSpec = flexible_gridspec_factory(mgridspec.GridSpec)
FlexibleGridSpec.__name__ = 'FlexibleGridSpec'
FlexibleGridSpecFromSubplotSpec = flexible_gridspec_factory(mgridspec.GridSpecFromSubplotSpec)
FlexibleGridSpecFromSubplotSpec.__name__ = 'FlexibleGridSpecFromSubplotSpec'
